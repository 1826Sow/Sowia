package com.sowkeys.sowia

import android.content.Intent
import android.os.Bundle
import androidx.activity.ComponentActivity

/**
 * The launcher first presents the official SOW IA showcase screen.
 * The user enters the existing Streamlit dashboard through its VALIDER button.
 */
class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        startActivity(Intent(this, VitrineActivity::class.java))
        finish()
    }
}
