package com.sowkeys.sowia

import android.content.Intent
import android.os.Bundle
import androidx.activity.ComponentActivity

/**
 * The Streamlit dashboard is the canonical SOW IA application and owns
 * the production Supabase sign-in/session. Starting a second native
 * sign-in here created two unrelated login prompts for the same user.
 *
 * Keep the Android package as a lightweight WebView launcher so users
 * authenticate once in the full dashboard and retain its browser session.
 */
class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        startActivity(Intent(this, DashboardActivity::class.java))
        finish()
    }
}
