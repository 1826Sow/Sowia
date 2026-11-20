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
import androidx.compose.foundation.layout.safeDrawingPadding
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
import androidx.compose.material3.TextButton
import androidx.compose.material3.OutlinedTextFieldDefaults
import androidx.compose.ui.text.input.VisualTransformation
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
        setContent { SowiaPrototype(openLogin = intent.getBooleanExtra("open_login", false)) }
    }
}

@Composable
private fun SowiaPrototype(openLogin: Boolean = false) {
    val navigationStack = remember { mutableStateListOf(if (openLogin) "Compte & paramètres" else "Accueil") }
    val screen = navigationStack.last()
    var selectedConversationId by remember { mutableStateOf<String?>(null) }
    var selectedWorkspace by remember { mutableStateOf("personal") }
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
                    .safeDrawingPadding()
                    .padding(20.dp),
            ) {
                if (screen != "Accueil") {
                    OutlinedButton(
                        onClick = { goBack() },
                        modifier = Modifier.fillMaxWidth(),
                        colors = ButtonDefaults.outlinedButtonColors(contentColor = Cyan),
                    ) { Text("←  Retour") }
                    Spacer(Modifier.height(12.dp))
                }
                Column(
                    modifier = Modifier
                        .fillMaxWidth()
                        .weight(1f)
                        .verticalScroll(rememberScrollState()),
                ) {
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
                        "Connexion sécurisée, assistant IA et documents privés",
                        color = Muted,
                        modifier = Modifier.padding(top = 8.dp, bottom = 16.dp),
                    )
                    Card(
                        modifier = Modifier.fillMaxWidth().padding(bottom = 20.dp),
                        colors = CardDefaults.cardColors(containerColor = Panel),
                    ) {
                        Column(
                            modifier = Modifier.fillMaxWidth().padding(16.dp),
                            verticalArrangement = Arrangement.spacedBy(12.dp),
                        ) {
                            Text("Choisissez votre espace", color = Color.White, fontWeight = FontWeight.SemiBold)
                            Row(
                                modifier = Modifier.fillMaxWidth(),
                                horizontalArrangement = Arrangement.spacedBy(8.dp),
                            ) {
                                Button(
                                    onClick = { selectedWorkspace = "personal" },
                                    modifier = Modifier.weight(1f),
                                    colors = ButtonDefaults.buttonColors(
                                        containerColor = if (selectedWorkspace == "personal") Cyan else Navy,
                                        contentColor = if (selectedWorkspace == "personal") Navy else Color.White,
                                    ),
                                ) { Text("Personnel") }
                                Button(
                                    onClick = { selectedWorkspace = "professional" },
                                    modifier = Modifier.weight(1f),
                                    colors = ButtonDefaults.buttonColors(
                                        containerColor = if (selectedWorkspace == "professional") Cyan else Navy,
                                        contentColor = if (selectedWorkspace == "professional") Navy else Color.White,
                                    ),
                                ) { Text("Professionnel") }
                            }
                            Button(
                                onClick = { navigate("Assistant") },
                                modifier = Modifier.fillMaxWidth(),
                                colors = ButtonDefaults.buttonColors(containerColor = Cyan, contentColor = Navy),
                            ) { Text("Valider") }
                        }
                    }
                    Card(
                        modifier = Modifier.fillMaxWidth().padding(bottom = 16.dp),
                        colors = CardDefaults.cardColors(containerColor = Panel),
                    ) {
                        Column(
                            modifier = Modifier.fillMaxWidth().padding(16.dp),
                            verticalArrangement = Arrangement.spacedBy(10.dp),
                        ) {
                            Text("Accès à votre compte", color = Color.White, fontWeight = FontWeight.SemiBold)
                            Text("Ouvrez la page de connexion pour saisir votre adresse e-mail et votre mot de passe.", color = Muted)
                            Button(
                                onClick = { navigate("Compte & paramètres") },
                                modifier = Modifier.fillMaxWidth().height(56.dp),
                                colors = ButtonDefaults.buttonColors(containerColor = Cyan, contentColor = Navy),
                            ) {
                                Text("Connexion — Valider", fontSize = 17.sp, fontWeight = FontWeight.Bold)
                            }
                        }
                    }
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
                        "Assistant" -> AssistantPanel(initialSessionId = selectedConversationId, workspaceId = selectedWorkspace, onOpenAccount = { navigate("Compte & paramètres") })
                        "Mes échanges & projets" -> RegistryPanel(onOpenAccount = { navigate("Compte & paramètres") }, onOpenConversation = { id, space -> selectedConversationId = id; selectedWorkspace = space; navigate("Assistant") })
                        "Laboratoire PDF" -> PdfLabPanel(onOpenAccount = { navigate("Compte & paramètres") })
                        else -> Card(colors = CardDefaults.cardColors(containerColor = Panel)) {
                            Column(Modifier.padding(18.dp)) {
                                Text("Rubrique en préparation", color = Cyan, fontWeight = FontWeight.Bold)
                                Spacer(Modifier.height(8.dp))
                                Text("Ce module sera activé après raccordement de ses services.", color = Muted)
                            }
                        }
                    }
                }
                Spacer(Modifier.height(24.dp))
                Text("SOW IA • Android 0.2.10 • Modules en intégration", color = Muted, fontSize = 11.sp)
                }
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
    var passwordVisible by remember { mutableStateOf(false) }
    var session by remember { mutableStateOf(auth.currentSession()) }
    var status by remember { mutableStateOf("") }
    var busy by remember { mutableStateOf(false) }

    LaunchedEffect(auth) {
        if (session != null && auth.isConfigured) {
            busy = true
            try {
                session = auth.validSession()
                status = if (session == null) {
                    "Session expirée. Reconnectez-vous pour continuer."
                } else {
                    "Session sécurisée rétablie."
                }
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
                    textStyle = MaterialTheme.typography.bodyLarge.copy(color = Navy),
                    colors = OutlinedTextFieldDefaults.colors(
                        focusedTextColor = Navy,
                        unfocusedTextColor = Navy,
                        focusedContainerColor = Color.White,
                        unfocusedContainerColor = Color.White,
                        focusedLabelColor = Navy,
                        unfocusedLabelColor = Navy,
                        focusedBorderColor = Cyan,
                        unfocusedBorderColor = Navy,
                        cursorColor = Cyan,
                    ),
                )
                OutlinedTextField(
                    value = password,
                    onValueChange = { password = it },
                    modifier = Modifier.fillMaxWidth(),
                    label = { Text("Mot de passe") },
                    singleLine = true,
                    visualTransformation = if (passwordVisible) VisualTransformation.None else PasswordVisualTransformation(),
                    trailingIcon = {
                        TextButton(onClick = { passwordVisible = !passwordVisible }) {
                            Text(if (passwordVisible) "Masquer" else "Afficher", color = Cyan)
                        }
                    },
                    textStyle = MaterialTheme.typography.bodyLarge.copy(color = Navy),
                    colors = OutlinedTextFieldDefaults.colors(
                        focusedTextColor = Navy,
                        unfocusedTextColor = Navy,
                        focusedContainerColor = Color.White,
                        unfocusedContainerColor = Color.White,
                        focusedLabelColor = Navy,
                        unfocusedLabelColor = Navy,
                        focusedBorderColor = Cyan,
                        unfocusedBorderColor = Navy,
                        cursorColor = Cyan,
                    ),
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
                    enabled = !busy,
                    modifier = Modifier.fillMaxWidth().height(56.dp),
                    colors = ButtonDefaults.buttonColors(
                        containerColor = Cyan,
                        contentColor = Navy,
                        disabledContainerColor = Muted,
                        disabledContentColor = Navy,
                    ),
                ) { Text("VALIDER", fontSize = 18.sp, fontWeight = FontWeight.Bold) }
                if (!auth.isConfigured) {
                    Text(
                        "Configuration Supabase à fournir à la compilation. La clé publique est utilisée ; aucune clé secrète serveur n'est intégrée.",
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
private fun AssistantPanel(initialSessionId: String?, workspaceId: String, onOpenAccount: () -> Unit) {
    val context = LocalContext.current
    val auth = remember(context) { SupabaseAuthClient(context) }
    val scope = rememberCoroutineScope()
    val sessionId = remember(initialSessionId) { initialSessionId ?: UUID.randomUUID().toString() }
    val session = remember { mutableStateOf(auth.currentSession()) }
    val lines = remember { mutableStateListOf<ChatLine>() }
    var draft by remember { mutableStateOf("") }
    var status by remember { mutableStateOf("") }
    var busy by remember { mutableStateOf(false) }

    LaunchedEffect(auth) {
        if (session.value != null && auth.isConfigured) {
            runCatching { session.value = auth.validSession() }
        }
    }

    LaunchedEffect(sessionId, workspaceId, session.value?.userId) {
        if (session.value != null && initialSessionId != null) {
            busy = true
            status = "Chargement de la conversation…"
            try {
                val previous = auth.loadConversationMessages(sessionId, workspaceId)
                lines.clear()
                lines.addAll(previous.map { ChatLine(it.optString("role"), it.optString("content")) })
                status = if (previous.isEmpty()) "Cette conversation ne contient aucun message." else ""
            } catch (error: Exception) {
                status = error.message ?: "Impossible de rouvrir cette conversation."
            } finally {
                busy = false
            }
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
                                    val answer = auth.sendChatMessage(sessionId, outgoing, workspaceId)
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
    val sessionId: String? = null,
    val projectId: Long? = null,
)

@Composable
private fun RegistryPanel(onOpenAccount: () -> Unit, onOpenConversation: (String, String) -> Unit) {
    val context = LocalContext.current
    val auth = remember(context) { SupabaseAuthClient(context) }
    val scope = rememberCoroutineScope()
    val conversations = remember { mutableStateListOf<RegistryEntry>() }
    val projects = remember { mutableStateListOf<RegistryEntry>() }
    var workspace by remember { mutableStateOf("personal") }
    var busy by remember { mutableStateOf(false) }
    var status by remember { mutableStateOf("") }
    var signedIn by remember { mutableStateOf(auth.currentSession() != null) }
    var newProjectTitle by remember { mutableStateOf("") }
    var newProjectDescription by remember { mutableStateOf("") }
    var editingProjectId by remember { mutableStateOf<Long?>(null) }
    var editProjectTitle by remember { mutableStateOf("") }
    var editProjectDescription by remember { mutableStateOf("") }

    fun reload() {
        if (!signedIn) return
        busy = true
        status = ""
        scope.launch {
            try {
                // Refresh the encrypted session before loading private registry data.
                // If refresh fails or the user has signed out, clear stale private rows.
                val currentSession = auth.validSession()
                if (currentSession == null) {
                    conversations.clear()
                    projects.clear()
                    signedIn = false
                    status = "Session expirée. Reconnectez-vous pour retrouver vos données."
                    return@launch
                }
                val conversationRows = auth.loadConversations(workspace)
                val projectRows = auth.loadProjects(workspace)
                conversations.clear()
                conversations.addAll(conversationRows.map {
                    RegistryEntry(
                        title = it.optString("title", "Conversation"),
                        detail = "Session : ${it.optString("session_id")}",
                        sessionId = it.optString("session_id"),
                    )
                })
                projects.clear()
                projects.addAll(projectRows.map {
                    RegistryEntry(
                        title = it.optString("title", "Projet"),
                        detail = it.optString("description"),
                        status = it.optString("status"),
                        projectId = it.optLong("id").takeIf { id -> id > 0L },
                    )
                })
                status = "Données actualisées depuis votre espace sécurisé."
            } catch (error: Exception) {
                // Never leave previously loaded private rows visible after a failed refresh.
                conversations.clear()
                projects.clear()
                if (auth.currentSession() == null) {
                    signedIn = false
                    status = "Session expirée. Reconnectez-vous pour retrouver vos données."
                } else {
                    status = error.message ?: "Actualisation impossible. Réessayez."
                }
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
                        Button(
                            onClick = { item.sessionId?.let { onOpenConversation(it, workspace) } },
                            enabled = !item.sessionId.isNullOrBlank(),
                            colors = ButtonDefaults.buttonColors(containerColor = Cyan, contentColor = Navy),
                        ) { Text("Rouvrir la conversation") }
                    }
                }

                Text("PROJETS", color = Cyan, fontWeight = FontWeight.Bold, fontSize = 12.sp)
                OutlinedTextField(
                    value = newProjectTitle,
                    onValueChange = { newProjectTitle = it.take(160) },
                    modifier = Modifier.fillMaxWidth(),
                    label = { Text("Nom du nouveau projet") },
                    singleLine = true,
                    enabled = !busy,
                    textStyle = MaterialTheme.typography.bodyLarge.copy(color = Navy),
                    colors = OutlinedTextFieldDefaults.colors(
                        focusedTextColor = Navy,
                        unfocusedTextColor = Navy,
                        focusedContainerColor = Color.White,
                        unfocusedContainerColor = Color.White,
                        focusedLabelColor = Navy,
                        unfocusedLabelColor = Navy,
                        focusedBorderColor = Cyan,
                        unfocusedBorderColor = Navy,
                        cursorColor = Cyan,
                    ),
                )
                OutlinedTextField(
                    value = newProjectDescription,
                    onValueChange = { newProjectDescription = it.take(4000) },
                    modifier = Modifier.fillMaxWidth(),
                    label = { Text("Description (facultative)") },
                    minLines = 2,
                    maxLines = 4,
                    enabled = !busy,
                    textStyle = MaterialTheme.typography.bodyLarge.copy(color = Navy),
                    colors = OutlinedTextFieldDefaults.colors(
                        focusedTextColor = Navy,
                        unfocusedTextColor = Navy,
                        focusedContainerColor = Color.White,
                        unfocusedContainerColor = Color.White,
                        focusedLabelColor = Navy,
                        unfocusedLabelColor = Navy,
                        focusedBorderColor = Cyan,
                        unfocusedBorderColor = Navy,
                        cursorColor = Cyan,
                    ),
                )
                Button(
                    onClick = {
                        busy = true
                        status = ""
                        scope.launch {
                            try {
                                auth.createProject(newProjectTitle, newProjectDescription, workspace)
                                newProjectTitle = ""
                                newProjectDescription = ""
                                val refreshed = auth.loadProjects(workspace)
                                projects.clear()
                                projects.addAll(refreshed.map {
                                    RegistryEntry(
                                        title = it.optString("title", "Projet"),
                                        detail = it.optString("description"),
                                        status = it.optString("status"),
                                        projectId = it.optLong("id").takeIf { id -> id > 0L },
                                    )
                                })
                                status = "Projet créé et enregistré."
                            } catch (error: Exception) {
                                status = error.message ?: "Création du projet impossible."
                            } finally {
                                busy = false
                            }
                        }
                    },
                    enabled = !busy && newProjectTitle.isNotBlank() && auth.isConfigured,
                    modifier = Modifier.fillMaxWidth(),
                    colors = ButtonDefaults.buttonColors(containerColor = Cyan, contentColor = Navy),
                ) { Text(if (busy) "Enregistrement…" else "Créer le projet") }
                if (projects.isEmpty() && !busy) Text("Aucun projet enregistré dans cet espace.", color = Muted)
                projects.forEach { item ->
                    Column(Modifier.fillMaxWidth().padding(vertical = 4.dp)) {
                        Text(item.title, color = Color.White, fontWeight = FontWeight.SemiBold)
                        if (item.detail.isNotBlank()) Text(item.detail, color = Muted, fontSize = 12.sp)
                        if (item.status.isNotBlank()) Text("État : ${item.status}", color = Cyan, fontSize = 11.sp)
                        if (item.projectId == editingProjectId) {
                            OutlinedTextField(
                                value = editProjectTitle,
                                onValueChange = { editProjectTitle = it.take(160) },
                                modifier = Modifier.fillMaxWidth(),
                                label = { Text("Nom du projet") },
                                singleLine = true,
                                enabled = !busy,
                                textStyle = MaterialTheme.typography.bodyLarge.copy(color = Navy),
                                colors = OutlinedTextFieldDefaults.colors(
                                    focusedTextColor = Navy,
                                    unfocusedTextColor = Navy,
                                    focusedContainerColor = Color.White,
                                    unfocusedContainerColor = Color.White,
                                    focusedLabelColor = Navy,
                                    unfocusedLabelColor = Navy,
                                    focusedBorderColor = Cyan,
                                    unfocusedBorderColor = Navy,
                                    cursorColor = Cyan,
                                ),
                            )
                            OutlinedTextField(
                                value = editProjectDescription,
                                onValueChange = { editProjectDescription = it.take(4000) },
                                modifier = Modifier.fillMaxWidth(),
                                label = { Text("Description du projet") },
                                minLines = 2,
                                maxLines = 4,
                                enabled = !busy,
                                textStyle = MaterialTheme.typography.bodyLarge.copy(color = Navy),
                                colors = OutlinedTextFieldDefaults.colors(
                                    focusedTextColor = Navy,
                                    unfocusedTextColor = Navy,
                                    focusedContainerColor = Color.White,
                                    unfocusedContainerColor = Color.White,
                                    focusedLabelColor = Navy,
                                    unfocusedLabelColor = Navy,
                                    focusedBorderColor = Cyan,
                                    unfocusedBorderColor = Navy,
                                    cursorColor = Cyan,
                                ),
                            )
                            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                                Button(
                                    onClick = {
                                        val id = item.projectId ?: return@Button
                                        busy = true
                                        scope.launch {
                                            try {
                                                auth.updateProject(id, editProjectTitle, editProjectDescription, workspace)
                                                val refreshed = auth.loadProjects(workspace)
                                                projects.clear()
                                                projects.addAll(refreshed.map {
                                                    RegistryEntry(
                                                        title = it.optString("title", "Projet"),
                                                        detail = it.optString("description"),
                                                        status = it.optString("status"),
                                                        projectId = it.optLong("id").takeIf { rowId -> rowId > 0L },
                                                    )
                                                })
                                                editingProjectId = null
                                                status = "Projet modifié et enregistré."
                                            } catch (error: Exception) {
                                                status = error.message ?: "Modification du projet impossible."
                                            } finally {
                                                busy = false
                                            }
                                        }
                                    },
                                    enabled = !busy && editProjectTitle.isNotBlank() && item.projectId != null,
                                    colors = ButtonDefaults.buttonColors(containerColor = Cyan, contentColor = Navy),
                                ) { Text(if (busy) "Enregistrement…" else "Enregistrer") }
                                OutlinedButton(
                                    onClick = { editingProjectId = null },
                                    enabled = !busy,
                                ) { Text("Annuler") }
                            }
                        } else {
                            OutlinedButton(
                                onClick = {
                                    editingProjectId = item.projectId
                                    editProjectTitle = item.title
                                    editProjectDescription = item.detail
                                },
                                enabled = !busy && item.projectId != null,
                            ) { Text("Modifier le projet") }
                        }
                        val nextStatus = when (item.status) {
                            "En cours" -> "À tester"
                            "À tester" -> "Validé"
                            "Validé" -> "Terminé"
                            else -> "En cours"
                        }
                        OutlinedButton(
                            onClick = {
                                val id = item.projectId
                                if (id != null) {
                                    busy = true
                                    scope.launch {
                                        try {
                                            auth.updateProjectStatus(id, nextStatus, workspace)
                                            val refreshed = auth.loadProjects(workspace)
                                            projects.clear()
                                            projects.addAll(refreshed.map {
                                                RegistryEntry(
                                                    title = it.optString("title", "Projet"),
                                                    detail = it.optString("description"),
                                                    status = it.optString("status"),
                                                    projectId = it.optLong("id").takeIf { rowId -> rowId > 0L },
                                                )
                                            })
                                            status = "État du projet mis à jour."
                                        } catch (error: Exception) {
                                            status = error.message ?: "Modification du projet impossible."
                                        } finally {
                                            busy = false
                                        }
                                    }
                                }
                            },
                            enabled = !busy && item.projectId != null,
                        ) { Text("Passer à : $nextStatus") }
                    }
                }
                if (status.isNotBlank()) Text(status, color = Cyan, fontSize = 12.sp)
            }
        }
    }
}
