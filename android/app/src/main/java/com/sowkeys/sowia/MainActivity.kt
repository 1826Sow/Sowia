package com.sowkeys.sowia

import android.content.Intent
import android.os.Bundle
import androidx.activity.ComponentActivity

/**
 * Launch the official SOW IA welcome screen first.
 * The dashboard remains the existing Streamlit service and is opened only
 * after the user validates the welcome screen.
 */
class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        startActivity(Intent(this, VitrineActivity::class.java))
        finish()
    }
}
