package com.sowkeys.sowia

import android.annotation.SuppressLint
import android.graphics.Bitmap
import android.net.Uri
import android.os.Bundle
import android.view.View
import android.webkit.CookieManager
import android.webkit.ValueCallback
import android.webkit.WebChromeClient
import android.webkit.WebResourceRequest
import android.webkit.WebView
import android.webkit.WebViewClient
import android.widget.FrameLayout
import android.widget.ProgressBar
import androidx.activity.ComponentActivity
import androidx.activity.OnBackPressedCallback
import androidx.activity.result.ActivityResultLauncher
import androidx.activity.result.contract.ActivityResultContracts

/**
 * Opens the existing SOW IA dashboard inside the Android application.
 * The native shell never injects credentials or privileged JavaScript bridges.
 */
class DashboardActivity : ComponentActivity() {
    private lateinit var webView: WebView
    private lateinit var pdfPickerLauncher: ActivityResultLauncher<Array<String>>
    private var pendingFileChooserCallback: ValueCallback<Array<Uri>>? = null

    @SuppressLint("SetJavaScriptEnabled")
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        // Android's system document picker is the supported source for PDF uploads.
        // Keep the callback until the user chooses a file or cancels the picker.
        pdfPickerLauncher = registerForActivityResult(ActivityResultContracts.OpenDocument()) { uri ->
            val callback = pendingFileChooserCallback
            pendingFileChooserCallback = null
            callback?.onReceiveValue(if (uri == null) null else arrayOf(uri))
        }

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
            // Required for WebView to read the content:// URI returned by Android's PDF picker.
            settings.allowContentAccess = true
            settings.javaScriptCanOpenWindowsAutomatically = false
            settings.setSupportMultipleWindows(false)
            settings.mixedContentMode = android.webkit.WebSettings.MIXED_CONTENT_NEVER_ALLOW

            val cookies = CookieManager.getInstance()
            cookies.setAcceptCookie(true)
            // Streamlit/Supabase authentication may use cross-site session cookies.
            cookies.setAcceptThirdPartyCookies(this, true)

            webChromeClient = object : WebChromeClient() {
                override fun onProgressChanged(view: WebView?, newProgress: Int) {
                    progress.visibility = if (newProgress >= 100) View.GONE else View.VISIBLE
                }

                override fun onShowFileChooser(
                    webView: WebView?,
                    filePathCallback: ValueCallback<Array<Uri>>?,
                    fileChooserParams: FileChooserParams?,
                ): Boolean {
                    if (filePathCallback == null) return false

                    // A new chooser request supersedes any unfinished request.
                    pendingFileChooserCallback?.onReceiveValue(null)
                    pendingFileChooserCallback = filePathCallback
                    return try {
                        pdfPickerLauncher.launch(arrayOf("application/pdf"))
                        true
                    } catch (_: Exception) {
                        pendingFileChooserCallback = null
                        filePathCallback.onReceiveValue(null)
                        false
                    }
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
                // Use SOW IA's own navigation history before leaving the dashboard.
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
        pendingFileChooserCallback?.onReceiveValue(null)
        pendingFileChooserCallback = null
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
