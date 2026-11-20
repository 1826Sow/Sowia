package com.sowkeys.sowia

import kotlinx.coroutines.CompletableDeferred
import kotlinx.coroutines.async
import kotlinx.coroutines.runBlocking
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class SessionOperationGateTest {
    @Test
    fun logoutQueuedDuringRefreshRemovesTheRotatedSession() = runBlocking {
        var persistedSession: String? = "old-refresh-token"
        val refreshEntered = CompletableDeferred<Unit>()
        val finishRefresh = CompletableDeferred<Unit>()

        val refresh = async {
            SessionOperationGate.withLock {
                val observedSession = persistedSession
                refreshEntered.complete(Unit)
                finishRefresh.await()
                if (observedSession != null) {
                    persistedSession = "rotated-refresh-token"
                }
            }
        }

        refreshEntered.await()
        val logoutQueued = CompletableDeferred<Unit>()
        val logout = async {
            logoutQueued.complete(Unit)
            SessionOperationGate.withLock {
                persistedSession = null
            }
        }
        logoutQueued.await()
        assertTrue("Refresh must still be in flight", !refresh.isCompleted)

        finishRefresh.complete(Unit)
        refresh.await()
        logout.await()

        assertNull("Logout must be the final writer of session state", persistedSession)
    }

    @Test
    fun refreshStartingAfterLogoutCannotRestoreADeletedSession() = runBlocking {
        var persistedSession: String? = "old-refresh-token"

        SessionOperationGate.withLock {
            persistedSession = null
        }

        val refreshed = async {
            SessionOperationGate.withLock {
                val observedSession = persistedSession
                if (observedSession != null) {
                    persistedSession = "rotated-refresh-token"
                }
                observedSession
            }
        }

        assertNull(refreshed.await())
        assertNull(persistedSession)
    }
}
