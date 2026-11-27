package com.sowkeys.sowia

import android.annotation.SuppressLint
import android.content.ActivityNotFoundException
import android.content.Intent
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
 * The document picker is delegated to Android's system document provider.
 */
class DashboardActivity : ComponentActivity() {
    private lateinit var webView: WebView
    private lateinit var pdfPickerLauncher: ActivityResultLauncher<Intent>
    private var pendingFileChooser: ValueCallback<Array<Uri>>? = null

    @SuppressLint("SetJavaScriptEnabled")
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        // Keep the original result Intent so the URI read grant can be persisted.
        // WebView/Chromium reads the content URI after it is handed back to Streamlit.
        pdfPickerLauncher = registerForActivityResult(
            ActivityResultContracts.StartActivityForResult()
        ) { result ->
            val callback = pendingFileChooser
            pendingFileChooser = null
            val resultIntent = result.data
            val uri = if (result.resultCode == RESULT_OK) resultIntent?.data else null

            if (uri != null && resultIntent != null) {
                val grantedFlags = resultIntent.flags and Intent.FLAG_GRANT_READ_URI_PERMISSION
                if (grantedFlags != 0) {
                    try {
                        contentResolver.takePersistableUriPermission(uri, grantedFlags)
                    } catch (_: SecurityException) {
                        // Some document providers grant only temporary read access.
                        // Preserve the URI callback; WebView can still try that grant.
                    }
                }
            }
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

                    // Some Android document providers report PDFs with a generic or
                    // inconsistent MIME type. A strict application/pdf filter can make
                    // visible PDF rows appear disabled or unselectable. Let the provider
                    // show selectable documents; Streamlit validates PDF extension and
                    // file signature before accepting the upload.
                    val pickerIntent = Intent(Intent.ACTION_OPEN_DOCUMENT).apply {
                        addCategory(Intent.CATEGORY_OPENABLE)
                        type = "*/*"
                        addFlags(
                            Intent.FLAG_GRANT_READ_URI_PERMISSION or
                                Intent.FLAG_GRANT_PERSISTABLE_URI_PERMISSION
                        )
                    }

                    return try {
                        pdfPickerLauncher.launch(pickerIntent)
                        true
                    } catch (_: ActivityNotFoundException) {
                        pendingFileChooser = null
                        filePathCallback.onReceiveValue(null)
                        false
                    } catch (_: SecurityException) {
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
