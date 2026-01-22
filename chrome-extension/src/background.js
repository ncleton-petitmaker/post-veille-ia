/**
 * Veille IA - Background Service Worker
 * Gère la communication avec l'app Claude Veille et le scheduling
 */

console.log('[VeilleIA] Service worker chargé!')

// Configuration
const CONFIG = {
  apiUrl: 'http://127.0.0.1:3847', // Port de l'API locale (127.0.0.1 au lieu de localhost pour éviter les restrictions Chrome)
  checkInterval: 60000, // Vérifier toutes les minutes
  retryDelay: 300000 // Réessayer après 5 minutes en cas d'échec
}

// État global
let scheduledPosts = []
let isConnected = false
let linkedInTabId = null
let checkIntervalId = null

/**
 * Initialisation au démarrage
 */
chrome.runtime.onInstalled.addListener(() => {
  console.log('[VeilleIA Background] Extension installée')
  startScheduleChecker()
})

chrome.runtime.onStartup.addListener(() => {
  console.log('[VeilleIA Background] Extension démarrée')
  startScheduleChecker()
})

/**
 * Démarre la vérification périodique des posts programmés
 */
function startScheduleChecker() {
  if (checkIntervalId) {
    clearInterval(checkIntervalId)
  }

  // Vérification initiale
  checkScheduledPosts()

  // Vérification périodique
  checkIntervalId = setInterval(checkScheduledPosts, CONFIG.checkInterval)

  console.log('[VeilleIA Background] Checker démarré')
}

/**
 * Vérifie s'il y a des posts à publier maintenant
 */
async function checkScheduledPosts() {
  console.log('[VeilleIA Background] Vérification des posts programmés...')

  try {
    // Récupérer les posts depuis l'API locale
    const response = await fetch(`${CONFIG.apiUrl}/api/scheduled-posts`, {
      method: 'GET',
      mode: 'cors',
      headers: {
        'Accept': 'application/json'
      }
    })

    if (!response.ok) {
      throw new Error(`API error: ${response.status}`)
    }

    const data = await response.json()
    scheduledPosts = data.posts || []

    // Filtrer les posts à publier maintenant
    const now = new Date()
    const postsToPublish = scheduledPosts.filter(post => {
      if (post.status !== 'scheduled') return false

      const scheduledDate = new Date(`${post.scheduled_date}T${post.scheduled_time}:00`)
      // Publier si l'heure programmée est passée (avec une marge de 5 minutes)
      const diff = now - scheduledDate
      return diff >= 0 && diff < 5 * 60 * 1000
    })

    if (postsToPublish.length > 0) {
      console.log(`[VeilleIA Background] ${postsToPublish.length} post(s) à publier`)

      for (const post of postsToPublish) {
        await publishPostToLinkedIn(post)
      }
    }

    isConnected = true

  } catch (error) {
    console.error('[VeilleIA Background] Erreur vérification:', error)
    isConnected = false

    // Essayer de charger depuis le storage local en backup
    const stored = await chrome.storage.local.get('scheduledPosts')
    if (stored.scheduledPosts) {
      scheduledPosts = stored.scheduledPosts
    }
  }
}

/**
 * Programme un post via le scheduler natif de LinkedIn
 * C'est LinkedIn qui gère la publication à l'heure prévue
 */
async function scheduleToLinkedInNative(post) {
  console.log('[VeilleIA Background] Programmation native LinkedIn:', post.title)

  try {
    // 1. S'assurer qu'on a un onglet LinkedIn ouvert
    linkedInTabId = await ensureLinkedInTab()

    // 2. Attendre que le content script soit prêt
    await waitForContentScript(linkedInTabId)

    // 3. Préparer les données du post avec l'image
    const postData = {
      id: post.id,
      title: post.title,
      content: post.content,
      scheduled_date: post.scheduled_date,
      scheduled_time: post.scheduled_time,
      image_url: post.image_url ? `${CONFIG.apiUrl}/api/image?path=${encodeURIComponent(post.image_url)}` : null
    }

    // 4. Envoyer la commande de programmation au content script
    const result = await chrome.tabs.sendMessage(linkedInTabId, {
      action: 'schedule',
      post: postData
    })

    // 5. Mettre à jour le statut
    if (result.success) {
      await updatePostStatus(post.id, 'scheduled_linkedin')
      console.log('[VeilleIA Background] Post programmé dans LinkedIn:', post.title)
    } else {
      await updatePostStatus(post.id, 'failed', result.error)
      console.error('[VeilleIA Background] Échec programmation:', result.error)
    }

    return result

  } catch (error) {
    console.error('[VeilleIA Background] Erreur programmation native:', error)
    await updatePostStatus(post.id, 'failed', error.message)
    return { success: false, error: error.message }
  }
}

/**
 * Publie un post sur LinkedIn via le content script
 */
async function publishPostToLinkedIn(post) {
  console.log('[VeilleIA Background] Publication:', post.title)

  try {
    // 1. S'assurer qu'on a un onglet LinkedIn ouvert
    linkedInTabId = await ensureLinkedInTab()

    // 2. Attendre que le content script soit prêt
    await waitForContentScript(linkedInTabId)

    // 3. Préparer les données du post avec l'image
    const postData = {
      id: post.id,
      title: post.title,
      content: post.content,
      image_url: post.image_url ? `${CONFIG.apiUrl}/api/image?path=${encodeURIComponent(post.image_url)}` : null
    }

    // 4. Envoyer la commande de publication
    const result = await chrome.tabs.sendMessage(linkedInTabId, {
      action: 'publish',
      post: postData
    })

    // 5. Mettre à jour le statut
    if (result.success) {
      await updatePostStatus(post.id, 'published')
      console.log('[VeilleIA Background] Post publié avec succès:', post.title)
    } else {
      await updatePostStatus(post.id, 'failed', result.error)
      console.error('[VeilleIA Background] Échec publication:', result.error)
    }

    return result

  } catch (error) {
    console.error('[VeilleIA Background] Erreur publication:', error)
    await updatePostStatus(post.id, 'failed', error.message)
    return { success: false, error: error.message }
  }
}

/**
 * S'assure qu'un onglet LinkedIn est ouvert
 */
async function ensureLinkedInTab() {
  // Chercher un onglet LinkedIn existant
  const tabs = await chrome.tabs.query({ url: 'https://www.linkedin.com/*' })

  if (tabs.length > 0) {
    // Utiliser l'onglet existant
    const tab = tabs[0]
    await chrome.tabs.update(tab.id, { active: true })

    // Si pas sur le feed, naviguer
    if (!tab.url.includes('/feed')) {
      await chrome.tabs.update(tab.id, { url: 'https://www.linkedin.com/feed/' })
      await sleep(3000)
    }

    return tab.id
  }

  // Créer un nouvel onglet LinkedIn
  const newTab = await chrome.tabs.create({
    url: 'https://www.linkedin.com/feed/',
    active: true
  })

  // Attendre le chargement
  await sleep(5000)

  return newTab.id
}

/**
 * Attend que le content script soit prêt
 */
function waitForContentScript(tabId, timeout = 30000) {
  return new Promise((resolve, reject) => {
    const startTime = Date.now()

    const check = async () => {
      try {
        const response = await chrome.tabs.sendMessage(tabId, { action: 'checkReady' })
        if (response && response.ready) {
          resolve()
          return
        }
      } catch (e) {
        // Content script pas encore chargé
      }

      if (Date.now() - startTime > timeout) {
        reject(new Error('Content script timeout'))
        return
      }

      setTimeout(check, 1000)
    }

    check()
  })
}

/**
 * Met à jour le statut d'un post via l'API
 */
async function updatePostStatus(postId, status, error = null) {
  try {
    await fetch(`${CONFIG.apiUrl}/api/scheduled-posts/${postId}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ status, error, published_at: status === 'published' ? new Date().toISOString() : null })
    })
  } catch (e) {
    console.error('[VeilleIA Background] Erreur mise à jour statut:', e)
  }
}

/**
 * Utilitaire sleep
 */
function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms))
}

/**
 * Écoute les messages
 */
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  console.log('[VeilleIA Background] Message:', message)

  switch (message.action) {
    case 'contentScriptReady':
      console.log('[VeilleIA Background] Content script prêt dans tab:', sender.tab?.id)
      break

    case 'publishResult':
      console.log('[VeilleIA Background] Résultat publication:', message.result)
      break

    case 'getScheduledPosts':
      sendResponse({ posts: scheduledPosts, isConnected })
      break

    case 'getPostData':
      // Récupérer un post spécifique depuis l'API (pour le content script qui ne peut pas fetch à cause de CSP)
      (async () => {
        try {
          console.log('[VeilleIA Background] Fetch post:', message.postId)
          const response = await fetch(`${CONFIG.apiUrl}/api/scheduled-posts`)
          const data = await response.json()
          const post = data.posts?.find(p => p.id === message.postId)
          if (post) {
            // Si le post a une image, la convertir en base64
            if (post.image_url) {
              try {
                console.log('[VeilleIA Background] Fetch image:', post.image_url)
                const imageUrl = `${CONFIG.apiUrl}/api/image?path=${encodeURIComponent(post.image_url)}`
                const imgResponse = await fetch(imageUrl)
                const blob = await imgResponse.blob()
                const reader = new FileReader()
                const base64 = await new Promise((resolve) => {
                  reader.onloadend = () => resolve(reader.result)
                  reader.readAsDataURL(blob)
                })
                post.imageBase64 = base64
                console.log('[VeilleIA Background] Image convertie en base64')
              } catch (imgError) {
                console.error('[VeilleIA Background] Erreur image:', imgError)
                post.imageBase64 = null
              }
            }
            post.image_url = null // On utilise imageBase64 à la place
            sendResponse({ post })
          } else {
            sendResponse({ error: 'Post non trouvé' })
          }
        } catch (error) {
          console.error('[VeilleIA Background] Erreur fetch post:', error)
          sendResponse({ error: error.message })
        }
      })()
      return true

    case 'updatePostStatus':
      // Mettre à jour le statut d'un post
      (async () => {
        try {
          await fetch(`${CONFIG.apiUrl}/api/scheduled-posts/${message.postId}`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ status: message.status })
          })
          sendResponse({ success: true })
        } catch (error) {
          sendResponse({ error: error.message })
        }
      })()
      return true

    case 'forceCheck':
      checkScheduledPosts().then(() => sendResponse({ success: true }))
      return true

    case 'manualPublish':
      publishPostToLinkedIn(message.post).then(result => sendResponse(result))
      return true

    case 'scheduleToLinkedIn':
      // Programmer directement dans le scheduler natif de LinkedIn
      scheduleToLinkedInNative(message.post).then(result => sendResponse(result))
      return true

    case 'getStatus':
      sendResponse({
        isConnected,
        scheduledCount: scheduledPosts.filter(p => p.status === 'scheduled').length,
        linkedInTabId
      })
      break
  }
})

// Écoute les changements de tabs
chrome.tabs.onRemoved.addListener((tabId) => {
  if (tabId === linkedInTabId) {
    linkedInTabId = null
  }
})

// Démarrage immédiat
console.log('[VeilleIA] Démarrage immédiat du checker...')
startScheduleChecker()
