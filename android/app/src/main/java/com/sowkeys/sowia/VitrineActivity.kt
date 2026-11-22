package com.sowkeys.sowia

import android.content.Intent
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp

class VitrineActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            MaterialTheme {
                VitrineScreen {
                    startActivity(Intent(this, DashboardActivity::class.java))
                    finish()
                }
            }
        }
    }
}

@Composable
private fun VitrineScreen(onEnter: () -> Unit) {
    Box(
        modifier = Modifier
            .fillMaxSize()
            .background(
                Brush.verticalGradient(
                    colors = listOf(Color(0xFF06152E), Color(0xFF020817), Color(0xFF031D35))
                )
            )
    ) {
        Column(
            modifier = Modifier
                .fillMaxSize()
                .verticalScroll(rememberScrollState())
                .padding(horizontal = 20.dp, vertical = 14.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                verticalAlignment = Alignment.CenterVertically
            ) {
                Image(
                    painter = painterResource(id = R.drawable.sowia_vitrine),
                    contentDescription = "Identité visuelle SOW IA",
                    modifier = Modifier.size(width = 76.dp, height = 54.dp),
                    contentScale = ContentScale.Crop
                )
                Spacer(Modifier.width(12.dp))
                Column {
                    Text("SOW IA", color = Color.White, fontSize = 25.sp, fontWeight = FontWeight.Black)
                    Text("THINK BEYOND TODAY", color = Color(0xFF58D8FF), fontSize = 11.sp, fontWeight = FontWeight.Bold)
                }
            }

            HeroIntelligenceArtwork(
                modifier = Modifier
                    .fillMaxWidth()
                    .height(190.dp)
            )

            Text(
                "L’intelligence artificielle au service de vos ambitions",
                color = Color.White,
                fontSize = 23.sp,
                lineHeight = 28.sp,
                fontWeight = FontWeight.Bold,
                textAlign = TextAlign.Center
            )
            Text(
                "Recherche, développement et opportunités à l’échelle internationale.",
                color = Color(0xFFB8C9E2),
                fontSize = 14.sp,
                lineHeight = 20.sp,
                textAlign = TextAlign.Center
            )

            Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                FeatureLine("SOW IA", "Une plateforme d’intelligence et de développement.")
                FeatureLine("NIGHT ÉCHANGE", "La vision d’une bourse internationale aux applications.")
                FeatureLine("FINAL TECH", "L’ambition d’une puce de nouvelle génération.")
            }

            Spacer(Modifier.height(4.dp))
            Button(
                onClick = onEnter,
                modifier = Modifier
                    .fillMaxWidth()
                    .height(58.dp),
                shape = RoundedCornerShape(16.dp),
                colors = ButtonDefaults.buttonColors(
                    containerColor = Color(0xFF087DEB),
                    contentColor = Color.White
                )
            ) {
                Text("VALIDER", fontSize = 18.sp, fontWeight = FontWeight.Bold)
            }
            Text(
                "Tomorrow’s Applications. Tomorrow’s Technologies.",
                color = Color(0xFF6F91B8),
                fontSize = 10.sp,
                textAlign = TextAlign.Center
            )
        }
    }
}

@Composable
private fun FeatureLine(title: String, description: String) {
    Surface(
        modifier = Modifier.fillMaxWidth(),
        color = Color(0xFF102744),
        shape = RoundedCornerShape(12.dp)
    ) {
        Column(modifier = Modifier.padding(horizontal = 14.dp, vertical = 10.dp)) {
            Text(title, color = Color(0xFF63D9FF), fontSize = 12.sp, fontWeight = FontWeight.Bold)
            Text(description, color = Color(0xFFE4EDF9), fontSize = 12.sp, lineHeight = 17.sp)
        }
    }
}

@Composable
private fun HeroIntelligenceArtwork(modifier: Modifier = Modifier) {
    Canvas(modifier = modifier) {
        val center = Offset(size.width / 2f, size.height / 2f)
        val radius = size.minDimension * 0.34f
        val points = listOf(
            Offset(size.width * 0.18f, size.height * 0.30f),
            Offset(size.width * 0.30f, size.height * 0.72f),
            Offset(size.width * 0.78f, size.height * 0.22f),
            Offset(size.width * 0.84f, size.height * 0.68f),
            Offset(size.width * 0.50f, size.height * 0.08f),
            Offset(size.width * 0.52f, size.height * 0.92f)
        )
        points.forEach { point ->
            drawLine(
                color = Color(0x6658D8FF),
                start = center,
                end = point,
                strokeWidth = 2.2f
            )
        }
        drawCircle(
            brush = Brush.radialGradient(
                colors = listOf(Color(0xFF56DFFF), Color(0xFF1269C8), Color(0x221269C8)),
                center = center,
                radius = radius * 1.7f
            ),
            radius = radius * 1.7f,
            center = center
        )
        drawCircle(color = Color(0xFF071A35), radius = radius * 0.72f, center = center)
        drawCircle(color = Color(0xFF9AF0FF), radius = 5f, center = center)
        points.forEachIndexed { index, point ->
            drawCircle(
                color = if (index % 2 == 0) Color(0xFF68E2FF) else Color(0xFF9A8BFF),
                radius = 5.5f,
                center = point
            )
            drawCircle(color = Color(0x5587E8FF), radius = 12f, center = point)
        }
    }
}
