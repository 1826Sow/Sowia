package com.sowkeys.sowia

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.BackHandler
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import kotlinx.coroutines.launch
import java.util.UUID

private val Navy = Color(0xFF071426)
private val Panel = Color(0xFF10243D)
private val Cyan = Color(0xFF35D7F2)
private val Muted = Color(0xFFB7C7D9)

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent { SowiaPrototype() }
    }
}

@Composable
private fun SowiaPrototype() {
    val navigationStack = remember { mutableStateListOf("Accueil") }
    val screen = navigationStack.last()
    val sections = listOf(
        "Assistant",
        "Mes échanges & projets",
        "Laboratoire PDF",
        "Compte & paramètres",
    )
    fun navigate(destination: String) {
        if (navigationStack.lastOrNull() != destination) navigationStack.add(destination)
    }
    fun goBack() {
        if (navigationStack.size > 1) navigationStack.removeAt(navigationStack.lastIndex)
    }
    BackHandler(enabled = navigationStack.size > 1) { goBack() }

    MaterialTheme {
        Surface(modifier = Modifier.fillMaxSize(), color = Navy) {
            Column(
                modifier = Modifier
                    .fillMaxSize()
                    .verticalScroll(rememberScrollState())
                    .padding(20.dp),
            ) {
                if (screen != "Accueil") {
                    OutlinedButton(
                        onClick = { goBack() },
                        modifier = Modifier.fillMaxWidth(),
                        colors = ButtonDefaults.outlinedButtonColors(contentColor = Cyan),
                    ) { Text("←  Retour") }
                    Spacer(Modifier.height(16.dp))
                }
                Text("SOW IA", color = Cyan, fontSize = 28.sp, fontWeight = FontWeight.Bold)
                Text("Executive Intelligence Suite", color = Muted, fontSize = 13.sp)
                Spacer(Modifier.height(24.dp))

                if (screen == "Accueil") {
                    Text(
                        "Votre espace intelligent",
                        color = Color.White,
                        fontSize = 22.sp,
                        fontWeight = FontWeight.SemiBold,
                    )
                    Text(
                        "Socle Android natif — connexion sécurisée en préparation",
                        color = Muted,
                        modifier = Modifier.padding(top = 8.dp, bottom = 20.dp),
                    )
                    sections.forEach { item ->
                        Card(
                            modifier = Modifier.fillMaxWidth().padding(bottom = 12.dp),
                            colors = CardDefaults.cardColors(containerColor = Panel),
                        ) {
                            Row(
                                modifier = Modifier.fillMaxWidth().padding(16.dp),
                                horizontalArrangement = Arrangement.SpaceBetween,
                                verticalAlignment = Alignment.CenterVertically,
                            ) {
                                Text(item, color = Color.White, fontWeight = FontWeight.Medium)
                                Button(
                                    onClick = { navigate(item) },
                                    colors = ButtonDefaults.buttonColors(
                                        containerColor = Cyan,
                                        contentColor = Navy,
                                    ),
                                ) { Text("Ouvrir") }
                            }
                        }
                    }
                } else {
                    Text(
                        screen,
                        color = Color.White,
                        fontSize = 22.sp,
                        fontWeight = FontWeight.SemiBold,
                    )
                    Spacer(Modifier.height(12.dp))
                    when (screen) {
                        "Compte & paramètres" -> AccountPanel()
                        "Assistant" -> AssistantPanel(onOpenAccount = { navigate("Compte & paramètres") })
                        "Mes échanges & projets" -> RegistryPanel(onOpenAccount = { navigate("Compte & paramètres") })
                        else -> Card(colors = CardDefaults.cardColors(containerColor = Panel)) {
                            Column(Modifier.padding(18.dp)) {
                                Text("Connexion requise", color = Cyan, fontWeight = FontWeight.Bold)
                                Spacer(Modifier.height(8.dp))
                                Text(
                                    "Connectez votre compte SOW IA. Les données et outils seront activés après raccordement des services correspondants.",
                                    color = Muted,
                                )
                            }
                        }
                    }
                }
                Spacer(Modifier.height(24.dp))
                Text("SOW IA • Android 0.2.0 • Version de préparation", color = Muted, fontSize = 11.sp)
            }
        }
    }
}

@Composable
private fun AccountPanel() {
    val context = LocalContext.current
    val auth = remember(context) { SupabaseAuthClient(context) }
    val scope = rememberCoroutineScope()
    var email by remember { mutableStateOf("") }
    var password by remember { mutableStateOf("") }
    var session by remember { mutableStateOf(auth.currentSession()) }
    var status by remember { mutableStateOf("") }
    var busy by remember { mutableStateOf(false) }

    LaunchedEffect(auth) {
        if (session != null && auth.isConfigured) {
            busy = true
            try {
                session = auth.refreshSession()
                status = "Session sécurisée rétablie."
            } catch (_: Exception) {
                // Keep the encrypted session when the device is temporarily offline.
                status = "Session enregistrée sur cet appareil. Vérification réseau à la prochaine connexion."
            } finally {
                busy = false
            }
        }
    }

    Card(colors = CardDefaults.cardColors(containerColor = Panel)) {
        Column(
            Modifier.fillMaxWidth().padding(18.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            Text("Compte SOW IA", color = Cyan, fontWeight = FontWeight.Bold)
            if (session != null) {
                Text("Connecté : ${session?.email}", color = Color.White)
                Text("Compte utilisateur : ${session?.userId}", color = Muted, fontSize = 12.sp)
                Button(
                    onClick = {
                        busy = true
                        status = "Vérification du service mobile…"
                        scope.launch {
                            try {
                                status = auth.checkMobileHealth()
                            } catch (error: Exception) {
                                status = error.message ?: "Service mobile indisponible."
                            } finally {
                                busy = false
                            }
                        }
                    },
                    enabled = !busy && auth.isConfigured,
                    modifier = Modifier.fillMaxWidth(),
                    colors = ButtonDefaults.buttonColors(containerColor = Cyan, contentColor = Navy),
                ) { Text(if (busy) "Vérification…" else "Tester la connexion sécurisée") }
                Button(
                    onClick = {
                        busy = true
                        scope.launch {
                            auth.signOut()
                            session = null
                            busy = false
                            status = "Session fermée sur cet appareil."
                        }
                    },
                    enabled = !busy,
                    colors = ButtonDefaults.buttonColors(containerColor = Cyan, contentColor = Navy),
                ) { Text("Se déconnecter") }
            } else {
                Text("Connexion par e-mail et mot de passe Supabase.", color = Muted)
                OutlinedTextField(
                    value = email,
                    onValueChange = { email = it },
                    modifier = Modifier.fillMaxWidth(),
                    label = { Text("Adresse e-mail") },
                    singleLine = true,
                    keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Email),
                )
                OutlinedTextField(
                    value = password,
                    onValueChange = { password = it },
                    modifier = Modifier.fillMaxWidth(),
                    label = { Text("Mot de passe") },
                    singleLine = true,
                    visualTransformation = PasswordVisualTransformation(),
                )
                Button(
                    onClick = {
                        busy = true
                        status = ""
                        scope.launch {
                            try {
                                session = auth.signIn(email, password)
                                password = ""
                                status = "Connexion réussie."
                            } catch (error: Exception) {
                                status = error.message ?: "Connexion impossible."
                            } finally {
                                busy = false
                            }
                        }
                    },
                    enabled = !busy && auth.isConfigured,
                    modifier = Modifier.fillMaxWidth(),
                    colors = ButtonDefaults.buttonColors(containerColor = Cyan, contentColor = Navy),
                ) { Text(if (busy) "Connexion…" else "Se connecter") }
                if (!auth.isConfigured) {
                    Text(
                        "Configuration Supabase à fournir à la compilation. La clé publique anon est utilisée ; aucune clé secrète serveur n'est intégrée.",
                        color = Muted,
                    )
                }
            }
            if (status.isNotBlank()) Text(status, color = Cyan)
        }
    }
}


private data class ChatLine(val role: String, val content: String)

@Composable
private fun AssistantPanel(onOpenAccount: () -> Unit) {
    val context = LocalContext.current
    val auth = remember(context) { SupabaseAuthClient(context) }
    val scope = rememberCoroutineScope()
    val sessionId = remember { UUID.randomUUID().toString() }
    val session = remember { mutableStateOf(auth.currentSession()) }
    val lines = remember { mutableStateListOf<ChatLine>() }
    var draft by remember { mutableStateOf("") }
    var status by remember { mutableStateOf("") }
    var busy by remember { mutableStateOf(false) }

    LaunchedEffect(auth) {
        if (session.value != null && auth.isConfigured) {
            runCatching { session.value = auth.refreshSession() }
        }
    }

    Card(colors = CardDefaults.cardColors(containerColor = Panel)) {
        Column(
            Modifier.fillMaxWidth().padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            Text("Assistant SOW IA", color = Cyan, fontWeight = FontWeight.Bold)
            if (session.value == null) {
                Text("Connectez-vous pour utiliser l'Assistant sécurisé.", color = Muted)
                Button(
                    onClick = onOpenAccount,
                    modifier = Modifier.fillMaxWidth(),
                    colors = ButtonDefaults.buttonColors(containerColor = Cyan, contentColor = Navy),
                ) { Text("Ouvrir Compte & paramètres") }
            } else {
                if (lines.isEmpty()) {
                    Text("Votre conversation sera privée et associée à votre compte.", color = Muted)
                }
                lines.forEach { line ->
                    Column(Modifier.fillMaxWidth()) {
                        Text(
                            if (line.role == "user") "Vous" else "SOW IA",
                            color = Cyan,
                            fontWeight = FontWeight.SemiBold,
                            fontSize = 12.sp,
                        )
                        Text(line.content, color = Color.White)
                    }
                }
                OutlinedTextField(
                    value = draft,
                    onValueChange = { draft = it },
                    modifier = Modifier.fillMaxWidth(),
                    label = { Text("Votre message") },
                    minLines = 2,
                    maxLines = 5,
                    enabled = !busy,
                )
                Button(
                    onClick = {
                        val outgoing = draft.trim()
                        if (outgoing.isNotEmpty()) {
                            draft = ""
                            lines.add(ChatLine("user", outgoing))
                            busy = true
                            status = ""
                            scope.launch {
                                try {
                                    val answer = auth.sendChatMessage(sessionId, outgoing)
                                    lines.add(ChatLine("assistant", answer))
                                } catch (error: Exception) {
                                    status = error.message ?: "Le service Assistant est indisponible."
                                } finally {
                                    busy = false
                                }
                            }
                        }
                    },
                    enabled = !busy && draft.isNotBlank() && auth.isConfigured,
                    modifier = Modifier.fillMaxWidth(),
                    colors = ButtonDefaults.buttonColors(containerColor = Cyan, contentColor = Navy),
                ) { Text(if (busy) "SOW IA réfléchit…" else "Envoyer") }
                if (busy) Text("Connexion au moteur IA sécurisé…", color = Muted)
                if (status.isNotBlank()) Text(status, color = Cyan)
            }
        }
    }
}


private data class RegistryEntry(
    val title: String,
    val detail: String,
    val status: String = "",
)

@Composable
private fun RegistryPanel(onOpenAccount: () -> Unit) {
    val context = LocalContext.current
    val auth = remember(context) { SupabaseAuthClient(context) }
    val scope = rememberCoroutineScope()
    val conversations = remember { mutableStateListOf<RegistryEntry>() }
    val projects = remember { mutableStateListOf<RegistryEntry>() }
    var workspace by remember { mutableStateOf("personal") }
    var busy by remember { mutableStateOf(false) }
    var status by remember { mutableStateOf("") }
    var signedIn by remember { mutableStateOf(auth.currentSession() != null) }

    fun reload() {
        if (!signedIn) return
        busy = true
        status = ""
        scope.launch {
            try {
                val conversationRows = auth.loadConversations(workspace)
                val projectRows = auth.loadProjects(workspace)
                conversations.clear()
                conversations.addAll(conversationRows.map {
                    RegistryEntry(
                        title = it.optString("title", "Conversation"),
                        detail = "Session : ${it.optString("session_id")}",
                    )
                })
                projects.clear()
                projects.addAll(projectRows.map {
                    RegistryEntry(
                        title = it.optString("title", "Projet"),
                        detail = it.optString("description"),
                        status = it.optString("status"),
                    )
                })
                status = "Données actualisées depuis votre espace sécurisé."
            } catch (error: Exception) {
                status = error.message ?: "Impossible de charger vos données."
            } finally {
                busy = false
            }
        }
    }

    LaunchedEffect(workspace, signedIn) { if (signedIn) reload() }

    Card(colors = CardDefaults.cardColors(containerColor = Panel)) {
        Column(
            Modifier.fillMaxWidth().padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            Text("Mes échanges & projets", color = Cyan, fontWeight = FontWeight.Bold)
            if (!signedIn) {
                Text("Connectez-vous pour retrouver vos conversations et projets.", color = Muted)
                Button(
                    onClick = onOpenAccount,
                    modifier = Modifier.fillMaxWidth(),
                    colors = ButtonDefaults.buttonColors(containerColor = Cyan, contentColor = Navy),
                ) { Text("Ouvrir Compte & paramètres") }
            } else {
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    Button(
                        onClick = { workspace = "personal" },
                        colors = ButtonDefaults.buttonColors(
                            containerColor = if (workspace == "personal") Cyan else Navy,
                            contentColor = if (workspace == "personal") Navy else Color.White,
                        ),
                    ) { Text("Personnel") }
                    Button(
                        onClick = { workspace = "professional" },
                        colors = ButtonDefaults.buttonColors(
                            containerColor = if (workspace == "professional") Cyan else Navy,
                            contentColor = if (workspace == "professional") Navy else Color.White,
                        ),
                    ) { Text("Professionnel") }
                }
                Button(
                    onClick = { reload() },
                    enabled = !busy,
                    modifier = Modifier.fillMaxWidth(),
                    colors = ButtonDefaults.buttonColors(containerColor = Cyan, contentColor = Navy),
                ) { Text(if (busy) "Actualisation…" else "Actualiser") }

                Text("CONVERSATIONS", color = Cyan, fontWeight = FontWeight.Bold, fontSize = 12.sp)
                if (conversations.isEmpty() && !busy) Text("Aucune conversation enregistrée dans cet espace.", color = Muted)
                conversations.forEach { item ->
                    Column(Modifier.fillMaxWidth().padding(vertical = 4.dp)) {
                        Text(item.title, color = Color.White, fontWeight = FontWeight.SemiBold)
                        Text(item.detail, color = Muted, fontSize = 11.sp)
                    }
                }

                Text("PROJETS", color = Cyan, fontWeight = FontWeight.Bold, fontSize = 12.sp)
                if (projects.isEmpty() && !busy) Text("Aucun projet enregistré dans cet espace.", color = Muted)
                projects.forEach { item ->
                    Column(Modifier.fillMaxWidth().padding(vertical = 4.dp)) {
                        Text(item.title, color = Color.White, fontWeight = FontWeight.SemiBold)
                        if (item.detail.isNotBlank()) Text(item.detail, color = Muted, fontSize = 12.sp)
                        if (item.status.isNotBlank()) Text("État : ${item.status}", color = Cyan, fontSize = 11.sp)
                    }
                }
                if (status.isNotBlank()) Text(status, color = Cyan, fontSize = 12.sp)
            }
        }
    }
}
