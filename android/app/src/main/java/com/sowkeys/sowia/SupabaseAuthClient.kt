package com.sowkeys.sowia

import android.content.Context
import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyProperties
import android.util.Base64
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL
import java.security.KeyStore
import javax.crypto.Cipher
import javax.crypto.KeyGenerator
import javax.crypto.SecretKey
import javax.crypto.spec.GCMParameterSpec

data class SowiaSession(
    val accessToken: String,
    val refreshToken: String,
    val userId: String,
    val email: String,
)

/**
 * Minimal Supabase Auth client for the native Android shell.
 * Only the public anon key is used; service-role and AI provider keys never ship in the app.
 */
class SupabaseAuthClient(context: Context) {
    private val preferences = context.applicationContext
        .getSharedPreferences("sowia_secure_session", Context.MODE_PRIVATE)

    val isConfigured: Boolean
        get() = BuildConfig.SUPABASE_URL.startsWith("https://") &&
            BuildConfig.SUPABASE_ANON_KEY.isNotBlank()

    suspend fun signIn(email: String, password: String): SowiaSession =
        withContext(Dispatchers.IO) {
            check(isConfigured) {
                "Configuration Supabase absente. Le service de connexion n'est pas encore activé."
            }
            require(email.isNotBlank() && password.isNotBlank()) {
                "Saisissez votre adresse e-mail et votre mot de passe."
            }
            val response = request(
                "/auth/v1/token?grant_type=password",
                JSONObject().put("email", email.trim()).put("password", password),
                null,
            )
            val user = response.optJSONObject("user")
                ?: throw IllegalStateException("Réponse d'authentification invalide.")
            val session = SowiaSession(
                accessToken = response.optString("access_token"),
                refreshToken = response.optString("refresh_token"),
                userId = user.optString("id"),
                email = user.optString("email", email.trim()),
            )
            require(session.accessToken.isNotBlank() && session.refreshToken.isNotBlank() &&
                session.userId.isNotBlank()) {
                "La session reçue est incomplète."
            }
            saveSession(session)
            session
        }

    fun currentSession(): SowiaSession? = runCatching {
        val encoded = preferences.getString("session", null) ?: return null
        val json = JSONObject(decrypt(encoded))
        SowiaSession(
            json.getString("access_token"),
            json.getString("refresh_token"),
            json.getString("user_id"),
            json.optString("email"),
        )
    }.getOrNull()


    suspend fun refreshSession(): SowiaSession? = withContext(Dispatchers.IO) {
        val previous = currentSession() ?: return@withContext null
        val response = request(
            "/auth/v1/token?grant_type=refresh_token",
            JSONObject().put("refresh_token", previous.refreshToken),
            null,
        )
        val user = response.optJSONObject("user")
        val refreshed = SowiaSession(
            accessToken = response.optString("access_token"),
            refreshToken = response.optString("refresh_token"),
            userId = user?.optString("id").orEmpty().ifBlank { previous.userId },
            email = user?.optString("email").orEmpty().ifBlank { previous.email },
        )
        require(refreshed.accessToken.isNotBlank() && refreshed.refreshToken.isNotBlank()) {
            "Le renouvellement de session a renvoyé une réponse incomplète."
        }
        saveSession(refreshed)
        refreshed
    }


    suspend fun checkMobileHealth(): String = withContext(Dispatchers.IO) {
        check(isConfigured) { "Configuration Supabase absente." }
        val session = currentSession() ?: throw IllegalStateException("Connectez-vous avant le test.")
        val connection = (URL(BuildConfig.SUPABASE_URL.trimEnd('/') + "/functions/v1/mobile-health")
            .openConnection() as HttpURLConnection).apply {
            requestMethod = "GET"
            connectTimeout = 12000
            readTimeout = 15000
            setRequestProperty("apikey", BuildConfig.SUPABASE_ANON_KEY)
            setRequestProperty("Authorization", "Bearer ${session.accessToken}")
            setRequestProperty("Accept", "application/json")
        }
        try {
            val status = connection.responseCode
            val stream = if (status in 200..299) connection.inputStream else connection.errorStream
            val text = stream?.bufferedReader()?.use { it.readText() }.orEmpty()
            if (status !in 200..299) {
                throw IllegalStateException("Vérification refusée (HTTP $status).")
            }
            val result = JSONObject(text)
            check(result.optBoolean("ok") && result.optString("service") == "sowia-mobile-health") {
                "Réponse du service mobile invalide."
            }
            "Connexion sécurisée au service mobile confirmée."
        } finally {
            connection.disconnect()
        }
    }

    suspend fun sendChatMessage(sessionId: String, message: String, workspaceId: String = "personal"): String = withContext(Dispatchers.IO) {
        check(isConfigured) { "Configuration Supabase absente." }
        val session = currentSession() ?: throw IllegalStateException("Connectez-vous dans Compte & paramètres.")
        require(sessionId.isNotBlank() && message.isNotBlank()) { "Le message ne peut pas être vide." }
        val response = request(
            "/functions/v1/mobile-chat",
            JSONObject().put("session_id", sessionId).put("workspace_id", workspaceId).put("message", message.trim()),
            session.accessToken,
        )
        check(response.optBoolean("ok")) { "Le service Assistant a refusé la demande." }
        response.optString("answer").takeIf { it.isNotBlank() }
            ?: throw IllegalStateException("L'Assistant n'a pas renvoyé de réponse.")
    }

    suspend fun signOut() = withContext(Dispatchers.IO) {
        val session = currentSession()
        if (session != null && isConfigured) {
            runCatching { request("/auth/v1/logout", JSONObject(), session.accessToken) }
        }
        preferences.edit().remove("session").apply()
    }

    private fun saveSession(session: SowiaSession) {
        val json = JSONObject()
            .put("access_token", session.accessToken)
            .put("refresh_token", session.refreshToken)
            .put("user_id", session.userId)
            .put("email", session.email)
        preferences.edit().putString("session", encrypt(json.toString())).apply()
    }

    private fun request(path: String, body: JSONObject, bearer: String?): JSONObject {
        val connection = (URL(BuildConfig.SUPABASE_URL.trimEnd('/') + path)
            .openConnection() as HttpURLConnection).apply {
            requestMethod = "POST"
            connectTimeout = 15000
            readTimeout = 20000
            doOutput = true
            setRequestProperty("apikey", BuildConfig.SUPABASE_ANON_KEY)
            setRequestProperty("Content-Type", "application/json")
            setRequestProperty("Accept", "application/json")
            if (!bearer.isNullOrBlank()) setRequestProperty("Authorization", "Bearer $bearer")
        }
        return try {
            connection.outputStream.use {
                it.write(body.toString().toByteArray(Charsets.UTF_8))
            }
            val status = connection.responseCode
            val stream = if (status in 200..299) connection.inputStream else connection.errorStream
            val text = stream?.bufferedReader()?.use { it.readText() }.orEmpty()
            if (status !in 200..299) {
                val message = runCatching {
                    val error = JSONObject(text)
                    error.optString("msg").ifBlank { error.optString("error_description") }
                }.getOrDefault("")
                throw IllegalStateException(message.ifBlank {
                    "Connexion refusée (HTTP $status)."
                })
            }
            if (text.isBlank()) JSONObject() else JSONObject(text)
        } finally {
            connection.disconnect()
        }
    }

    private fun secretKey(): SecretKey {
        val store = KeyStore.getInstance("AndroidKeyStore").apply { load(null) }
        (store.getKey(KEY_ALIAS, null) as? SecretKey)?.let { return it }
        val generator = KeyGenerator.getInstance(
            KeyProperties.KEY_ALGORITHM_AES,
            "AndroidKeyStore",
        )
        generator.init(
            KeyGenParameterSpec.Builder(
                KEY_ALIAS,
                KeyProperties.PURPOSE_ENCRYPT or KeyProperties.PURPOSE_DECRYPT,
            ).setBlockModes(KeyProperties.BLOCK_MODE_GCM)
                .setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE)
                .setRandomizedEncryptionRequired(true)
                .build(),
        )
        return generator.generateKey()
    }

    private fun encrypt(value: String): String {
        val cipher = Cipher.getInstance("AES/GCM/NoPadding")
        cipher.init(Cipher.ENCRYPT_MODE, secretKey())
        val encrypted = cipher.doFinal(value.toByteArray(Charsets.UTF_8))
        return Base64.encodeToString(cipher.iv + encrypted, Base64.NO_WRAP)
    }

    private fun decrypt(value: String): String {
        val bytes = Base64.decode(value, Base64.NO_WRAP)
        require(bytes.size > 12) { "Session chiffrée invalide." }
        val cipher = Cipher.getInstance("AES/GCM/NoPadding")
        cipher.init(
            Cipher.DECRYPT_MODE,
            secretKey(),
            GCMParameterSpec(128, bytes.copyOfRange(0, 12)),
        )
        return String(cipher.doFinal(bytes.copyOfRange(12, bytes.size)), Charsets.UTF_8)
    }

    companion object {
        private const val KEY_ALIAS = "sowia.supabase.session.v1"
    }
}
