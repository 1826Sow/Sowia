package com.sowkeys.sowia

import android.annotation.SuppressLint
import android.graphics.Bitmap
import android.os.Bundle
import android.view.View
import android.webkit.CookieManager
import android.webkit.WebChromeClient
import android.webkit.WebResourceRequest
import android.webkit.WebView
import android.webkit.WebViewClient
import android.widget.FrameLayout
import android.widget.ProgressBar
import androidx.activity.ComponentActivity
import androidx.activity.OnBackPressedCallback

/**
 * Opens the existing SOW IA dashboard inside the Android application.
 * No credentials or JavaScript bridge are injected by the native shell.
 */
class DashboardActivity : ComponentActivity() {
    private lateinit var webView: WebView

    @SuppressLint("SetJavaScriptEnabled")
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        val container = FrameLayout(this)
        val progress = ProgressBar(this, null, android.R.attr.progressBarStyleHorizontal).apply {
            isIndeterminate = false
            max = 100
        }
        webView = WebView(this).apply {
            settings.javaScriptEnabled = true
            settings.domStorageEnabled = true
            settings.loadsImagesAutomatically = true
            settings.allowFileAccess = false
            settings.allowContentAccess = false
            settings.javaScriptCanOpenWindowsAutomatically = false
            settings.setSupportMultipleWindows(false)
            settings.mixedContentMode = android.webkit.WebSettings.MIXED_CONTENT_NEVER_ALLOW
            CookieManager.getInstance().setAcceptCookie(true)
            webChromeClient = object : WebChromeClient() {
                override fun onProgressChanged(view: WebView?, newProgress: Int) {
                    progress.visibility = if (newProgress >= 100) View.GONE else View.VISIBLE
                }
            }
            webViewClient = object : WebViewClient() {
                override fun onPageStarted(view: WebView?, url: String?, favicon: Bitmap?) {
                    progress.visibility = View.VISIBLE
                }

                override fun onPageFinished(view: WebView?, url: String?) {
                    progress.visibility = View.GONE
                }

                override fun shouldOverrideUrlLoading(view: WebView?, request: WebResourceRequest?): Boolean {
                    val uri = request?.url ?: return true
                    return uri.scheme != "https"
                }
            }
        }
        container.addView(
            webView,
            FrameLayout.LayoutParams(
                FrameLayout.LayoutParams.MATCH_PARENT,
                FrameLayout.LayoutParams.MATCH_PARENT,
            ),
        )
        container.addView(
            progress,
            FrameLayout.LayoutParams(
                FrameLayout.LayoutParams.MATCH_PARENT,
                4,
            ),
        )
        setContentView(container)

        onBackPressedDispatcher.addCallback(this, object : OnBackPressedCallback(true) {
            override fun handleOnBackPressed() {
                // Give SOW IA's own navigation stack first priority. This makes
                // the Android system Back button behave like the in-app Back
                // button instead of unexpectedly leaving the dashboard.
                webView.evaluateJavascript(
                    """(function() {
                        const button = document.querySelector(
                            '.st-key-sowia_navigation_back button'
                        );
                        if (button && !button.disabled) {
                            button.click();
                            return true;
                        }
                        return false;
                    })();""",
                    { handled ->
                        if (handled != "true") {
                            if (webView.canGoBack()) webView.goBack() else finish()
                        }
                    },
                )
            }
        })

        if (savedInstanceState == null) {
            webView.loadUrl(DASHBOARD_URL)
        } else {
            webView.restoreState(savedInstanceState)
        }
    }

    override fun onSaveInstanceState(outState: Bundle) {
        webView.saveState(outState)
        super.onSaveInstanceState(outState)
    }

    override fun onDestroy() {
        webView.stopLoading()
        webView.webChromeClient = null
        webView.webViewClient = WebViewClient()
        webView.destroy()
        super.onDestroy()
    }

    private companion object {
        const val DASHBOARD_URL = "https://fm5aczcvvj5jgkhpxwqtcr.streamlit.app/"
    }
}
