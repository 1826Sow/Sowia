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
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.mutableStateListOf
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp

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
    val sections = listOf("Assistant", "Mes échanges & projets", "Laboratoire PDF", "Compte & paramètres")

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
                    .padding(20.dp)
            ) {
                if (screen != "Accueil") {
                    OutlinedButton(
                        onClick = { goBack() },
                        modifier = Modifier.fillMaxWidth(),
                        colors = ButtonDefaults.outlinedButtonColors(contentColor = Cyan)
                    ) { Text("←  Retour") }
                    Spacer(Modifier.height(16.dp))
                }

                Text("SOW IA", color = Cyan, fontSize = 28.sp, fontWeight = FontWeight.Bold)
                Text("Executive Intelligence Suite", color = Muted, fontSize = 13.sp)
                Spacer(Modifier.height(24.dp))

                if (screen == "Accueil") {
                    Text("Votre espace intelligent", color = Color.White, fontSize = 22.sp, fontWeight = FontWeight.SemiBold)
                    Text(
                        "Prototype Android natif — socle d’interface en préparation",
                        color = Muted,
                        modifier = Modifier.padding(top = 8.dp, bottom = 20.dp)
                    )
                    sections.forEach { item ->
                        Card(
                            modifier = Modifier.fillMaxWidth().padding(bottom = 12.dp),
                            colors = CardDefaults.cardColors(containerColor = Panel)
                        ) {
                            Row(
                                modifier = Modifier.fillMaxWidth().padding(16.dp),
                                horizontalArrangement = Arrangement.SpaceBetween,
                                verticalAlignment = Alignment.CenterVertically
                            ) {
                                Text(item, color = Color.White, fontWeight = FontWeight.Medium)
                                Button(
                                    onClick = { navigate(item) },
                                    colors = ButtonDefaults.buttonColors(containerColor = Cyan, contentColor = Navy)
                                ) { Text("Ouvrir") }
                            }
                        }
                    }
                } else {
                    Text(screen, color = Color.White, fontSize = 22.sp, fontWeight = FontWeight.SemiBold)
                    Spacer(Modifier.height(12.dp))
                    Card(colors = CardDefaults.cardColors(containerColor = Panel)) {
                        Column(Modifier.padding(18.dp)) {
                            Text("Connexion aux services en attente", color = Cyan, fontWeight = FontWeight.Bold)
                            Spacer(Modifier.height(8.dp))
                            Text(
                                "Cet écran est une base d’interface. Aucune donnée personnelle n’est encore chargée : l’authentification native et les API sécurisées doivent être ajoutées et testées avant activation.",
                                color = Muted
                            )
                        }
                    }
                }

                Spacer(Modifier.height(24.dp))
                Text("SOW IA • Prototype 0.1.0 • Non publié", color = Muted, fontSize = 11.sp)
            }
        }
    }
}
