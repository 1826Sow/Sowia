package com.sowkeys.sowia

import android.annotation.SuppressLint
import android.content.ActivityNotFoundException
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
 * No credentials or JavaScript bridge are injected by the native shell.
 */
class DashboardActivity : ComponentActivity() {
    private lateinit var webView: WebView
    private lateinit var pdfPickerLauncher: ActivityResultLauncher<Array<String>>
    private var pendingFileChooser: ValueCallback<Array<Uri>>? = null

    @SuppressLint("SetJavaScriptEnabled")
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        // Streamlit's st.file_uploader uses the WebView file chooser callback.
        // Without this bridge, tapping the PDF picker appears to do nothing on Android.
        pdfPickerLauncher = registerForActivityResult(ActivityResultContracts.OpenDocument()) { uri ->
            val callback = pendingFileChooser
            pendingFileChooser = null
            callback?.onReceiveValue(uri?.let { arrayOf(it) })
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
            // Content URIs are supplied by Android's document picker, not arbitrary file paths.
            settings.allowContentAccess = true
            settings.javaScriptCanOpenWindowsAutomatically = false
            settings.setSupportMultipleWindows(false)
            settings.mixedContentMode = android.webkit.WebSettings.MIXED_CONTENT_NEVER_ALLOW
            CookieManager.getInstance().setAcceptCookie(true)
            webChromeClient = object : WebChromeClient() {
                override fun onProgressChanged(view: WebView?, newProgress: Int) {
                    progress.visibility = if (newProgress >= 100) View.GONE else View.VISIBLE
                }

                override fun onShowFileChooser(
                    view: WebView?,
                    filePathCallback: ValueCallback<Array<Uri>>?,
                    fileChooserParams: FileChooserParams?,
                ): Boolean {
                    if (filePathCallback == null) return false

                    // Complete any abandoned picker request before opening another one.
                    pendingFileChooser?.onReceiveValue(null)
                    pendingFileChooser = filePathCallback

                    val mimeTypes = fileChooserParams?.acceptTypes
                        .orEmpty()
                        .flatMap { it.split(",") }
                        .map { it.trim() }
                        .filter { it.contains("/") }
                        .distinct()
                        .ifEmpty { listOf("application/pdf") }

                    return try {
                        pdfPickerLauncher.launch(mimeTypes.toTypedArray())
                        true
                    } catch (_: ActivityNotFoundException) {
                        pendingFileChooser = null
                        filePathCallback.onReceiveValue(null)
                        false
                    } catch (_: IllegalStateException) {
                        pendingFileChooser = null
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
                    CookieManager.getInstance().flush()
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
                // Android system Back behave like the in-app Back button.
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
        pendingFileChooser?.onReceiveValue(null)
        pendingFileChooser = null
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
