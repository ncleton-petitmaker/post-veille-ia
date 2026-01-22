/**
 * Veille IA - LinkedIn Content Script
 * Gère la publication automatique des posts LinkedIn
 */

// État global
let isPublishing = false
let currentPost = null

// Sélecteurs LinkedIn (peuvent changer, à maintenir)
const SELECTORS = {
  // Bouton pour ouvrir le compositeur (zone de texte cliquable en haut du feed)
  startPostButton: '.share-box-feed-entry__trigger, .share-box-feed-entry__top-bar button, [data-test-id="share-box-trigger-button"], .share-box__open, button[aria-label*="Commencer"], button[aria-label*="Start a post"]',

  // Zone de texte du compositeur
  postTextArea: '.ql-editor, [role="textbox"][contenteditable="true"], .editor-content [contenteditable="true"], [data-placeholder*="quoi"][contenteditable="true"], div[contenteditable="true"][aria-label]',

  // Bouton d'ajout de média
  addMediaButton: '[aria-label*="Ajouter un média"], [aria-label*="Add media"], button[data-test-icon="image-medium"]',

  // Input file pour l'image (caché)
  fileInput: 'input[type="file"][accept*="image"]',

  // Bouton publier
  publishButton: '.share-actions__primary-action, [data-test-id="share-actions-primary-action"], button[aria-label*="Publier"], button[aria-label*="Post"]',

  // Bouton horloge pour programmer (scheduler natif LinkedIn)
  scheduleButton: '[aria-label*="Schedule"], [aria-label*="Programmer"], [aria-label*="horloge"], [aria-label*="clock"], button[data-test-icon="clock"], .schedule-post-button, .share-creation-state__footer button svg[data-test-icon="clock"]',

  // Modal de programmation
  scheduleModal: '.schedule-post-modal, [data-test-modal="schedule-post"]',

  // Sélecteur de date (dans le modal "Programmer un post")
  dateInput: 'input[id*="date"], input[name*="date"], input[placeholder*="date"], input[aria-label*="Date"], .scheduling-modal input:first-of-type',

  // Sélecteur d'heure
  timeInput: 'input[id*="time"], input[id*="heure"], input[name*="time"], input[aria-label*="Heure"], input[aria-label*="Time"], .scheduling-modal input:last-of-type',

  // Bouton confirmer programmation
  confirmScheduleButton: 'button[aria-label*="Schedule"], button[aria-label*="Programmer"]:not([data-test-icon="clock"]), .schedule-confirm-button',

  // Modal du compositeur
  composerModal: '.share-box-feed-entry__closed-share-box, .share-creation-state, [data-test-modal-id="share-modal"]',

  // Indicateur de chargement d'image
  imageUploading: '.share-media-upload-in-progress, [data-test-loading-indicator]',

  // Image uploadée
  uploadedImage: '.share-creation-state__image-container img, .share-box-image-thumbnail'
}

/**
 * Attend qu'un élément apparaisse dans le DOM
 */
function waitForElement(selector, timeout = 10000) {
  return new Promise((resolve, reject) => {
    const element = document.querySelector(selector)
    if (element) {
      resolve(element)
      return
    }

    const observer = new MutationObserver((mutations, obs) => {
      const el = document.querySelector(selector)
      if (el) {
        obs.disconnect()
        resolve(el)
      }
    })

    observer.observe(document.body, {
      childList: true,
      subtree: true
    })

    setTimeout(() => {
      observer.disconnect()
      reject(new Error(`Element ${selector} not found after ${timeout}ms`))
    }, timeout)
  })
}

/**
 * Attend que l'élément disparaisse
 */
function waitForElementToDisappear(selector, timeout = 30000) {
  return new Promise((resolve, reject) => {
    const checkInterval = setInterval(() => {
      const element = document.querySelector(selector)
      if (!element) {
        clearInterval(checkInterval)
        resolve()
      }
    }, 500)

    setTimeout(() => {
      clearInterval(checkInterval)
      reject(new Error(`Element ${selector} still present after ${timeout}ms`))
    }, timeout)
  })
}

/**
 * Simule une frappe de texte naturelle
 */
async function typeText(element, text) {
  // S'assurer que l'élément est bien focusable
  element.click()
  await sleep(200)
  element.focus()
  await sleep(200)

  // Vider le contenu existant
  element.innerHTML = ''

  // Méthode 1: Essayer avec innerHTML pour le texte multiligne
  const htmlContent = text.split('\n').map(line => {
    if (line.trim() === '') return '<br>'
    return `<p>${line}</p>`
  }).join('')

  element.innerHTML = htmlContent

  // Déclencher les événements
  element.dispatchEvent(new Event('input', { bubbles: true }))
  element.dispatchEvent(new Event('change', { bubbles: true }))

  await sleep(300)

  // Vérifier si le texte a été inséré
  if (element.innerText.length < text.length / 2) {
    console.log('[VeilleIA] innerHTML n\'a pas marché, essai avec execCommand')
    element.innerHTML = ''
    element.focus()
    document.execCommand('insertText', false, text)
    element.dispatchEvent(new Event('input', { bubbles: true }))
    await sleep(200)
  }

  console.log('[VeilleIA] Texte inséré, longueur:', element.innerText.length)
}

/**
 * Convertit une URL d'image en File object
 */
async function urlToFile(imageUrl) {
  try {
    // Si c'est une URL data:
    if (imageUrl.startsWith('data:')) {
      const response = await fetch(imageUrl)
      const blob = await response.blob()
      return new File([blob], 'post-image.png', { type: 'image/png' })
    }

    // Si c'est une URL HTTP
    const response = await fetch(imageUrl)
    const blob = await response.blob()
    const fileName = imageUrl.split('/').pop() || 'post-image.png'
    return new File([blob], fileName, { type: blob.type })
  } catch (error) {
    console.error('[VeilleIA] Erreur conversion image:', error)
    throw error
  }
}

/**
 * Upload une image dans le compositeur
 */
async function uploadImage(imageData) {
  console.log('[VeilleIA] Upload image...')

  // Cliquer sur le bouton d'ajout de média
  const addMediaBtn = await waitForElement(SELECTORS.addMediaButton, 5000)
  addMediaBtn.click()
  await sleep(300)

  // Trouver l'input file
  const fileInput = await waitForElement(SELECTORS.fileInput, 3000)

  // Créer le fichier
  let file
  if (typeof imageData === 'string') {
    file = await urlToFile(imageData)
  } else {
    file = imageData
  }

  // Créer un DataTransfer pour simuler le drop
  const dataTransfer = new DataTransfer()
  dataTransfer.items.add(file)
  fileInput.files = dataTransfer.files

  // Déclencher l'événement change
  fileInput.dispatchEvent(new Event('change', { bubbles: true }))

  console.log('[VeilleIA] Attente fin upload...')

  // Attendre que l'éditeur d'image apparaisse (signe que l'upload est fait)
  await sleep(500)
}

/**
 * Programme un post via le scheduler natif de LinkedIn
 */
async function schedulePostNative(post) {
  if (isPublishing) {
    throw new Error('Publication déjà en cours')
  }

  isPublishing = true
  currentPost = post

  try {
    console.log('[VeilleIA] Début programmation:', post.title)
    console.log('[VeilleIA] Date/Heure:', post.scheduled_date, post.scheduled_time)

    // 1. S'assurer qu'on est sur le feed LinkedIn
    if (!window.location.href.includes('linkedin.com/feed')) {
      window.location.href = 'https://www.linkedin.com/feed/'
      await sleep(2000)
    }

    // Scroll en haut de la page pour voir le bouton
    window.scrollTo(0, 0)
    await sleep(300)

    // 2. Ouvrir le compositeur
    console.log('[VeilleIA] Ouverture compositeur...')
    const startButton = await waitForElement(SELECTORS.startPostButton, 10000)
    startButton.click()

    // 3. Upload de l'image D'ABORD (car l'éditeur d'image réinitialise le texte)
    if (post.imageData || post.image_url) {
      // Attendre que le compositeur soit prêt
      await waitForElement(SELECTORS.postTextArea, 10000)
      await sleep(500)

      console.log('[VeilleIA] Upload de l\'image...')
      await uploadImage(post.imageData || post.image_url)

      // Passer l'éditeur d'image rapidement
      console.log('[VeilleIA] Recherche bouton Suivant (éditeur d\'image)...')

      for (let attempt = 0; attempt < 20; attempt++) {
        await sleep(150)

        const allButtons = Array.from(document.querySelectorAll('button'))
        const nextButton = allButtons.find(btn => {
          const text = btn.innerText.trim()
          return text === 'Suivant' || text === 'Next'
        })

        if (nextButton) {
          console.log('[VeilleIA] Bouton Suivant trouvé, clic...')
          nextButton.click()
          await sleep(400)

          // Vérifier s'il y a un autre bouton Suivant
          await sleep(300)
          const btns2 = Array.from(document.querySelectorAll('button'))
          const nextBtn2 = btns2.find(btn => btn.innerText.trim() === 'Suivant')
          if (nextBtn2) {
            console.log('[VeilleIA] Second Suivant, clic...')
            nextBtn2.click()
            await sleep(400)
          }
          break
        }
      }
    }

    // 4. ENSUITE insérer le texte (après l'éditeur d'image)
    console.log('[VeilleIA] Attente zone de texte...')
    const textArea = await waitForElement(SELECTORS.postTextArea, 10000)
    await sleep(800)

    console.log('[VeilleIA] Insertion du contenu...')
    await typeText(textArea, post.content)

    // Vérifier que le texte est bien inséré
    if (textArea.innerText.length < 10) {
      console.log('[VeilleIA] Texte non inséré, nouvelle tentative...')
      await sleep(500)
      textArea.click()
      textArea.focus()
      document.execCommand('selectAll', false, null)
      document.execCommand('insertText', false, post.content)
      await sleep(300)
    }

    // 5. Attendre un peu
    await sleep(300)

    // 7. Cliquer sur l'icône horloge pour ouvrir le scheduler
    console.log('[VeilleIA] Ouverture du scheduler LinkedIn...')

    // Essayer plusieurs méthodes pour trouver le bouton horloge
    let scheduleBtn = document.querySelector(SELECTORS.scheduleButton)

    if (!scheduleBtn) {
      // Chercher un bouton avec une icône horloge (SVG)
      const buttons = Array.from(document.querySelectorAll('button'))
      scheduleBtn = buttons.find(btn => {
        const svg = btn.querySelector('svg')
        if (!svg) return false
        // Vérifier si l'icône ressemble à une horloge (cercle + lignes)
        const paths = svg.querySelectorAll('path, circle')
        return paths.length > 0 && (
          btn.getAttribute('aria-label')?.toLowerCase().includes('schedule') ||
          btn.getAttribute('aria-label')?.toLowerCase().includes('program') ||
          btn.getAttribute('aria-label')?.toLowerCase().includes('horloge') ||
          btn.closest('.share-creation-state__footer')
        )
      })
    }

    if (!scheduleBtn) {
      // Dernier recours: chercher le bouton à côté de "Publier"
      const publishBtn = document.querySelector('button[aria-label*="Publier"], button[aria-label*="Post"]')
      if (publishBtn) {
        const footer = publishBtn.closest('.share-box-footer, .share-creation-state__footer, div')
        if (footer) {
          const clockBtn = footer.querySelector('button:not([aria-label*="Publier"]):not([aria-label*="Post"])')
          if (clockBtn) scheduleBtn = clockBtn
        }
      }
    }

    if (!scheduleBtn) {
      throw new Error('Bouton de programmation (horloge) non trouvé')
    }

    console.log('[VeilleIA] Bouton scheduler trouvé, clic...')
    scheduleBtn.click()
    await sleep(600)

    // 8. Remplir la date (format DD/MM/YYYY pour LinkedIn FR)
    console.log('[VeilleIA] Sélection de la date:', post.scheduled_date)
    // Trouver les inputs dans le modal de programmation
    const allInputs = Array.from(document.querySelectorAll('input[type="text"], input:not([type])'))
    const scheduleInputs = allInputs.filter(input => {
      const label = input.closest('label') || document.querySelector(`label[for="${input.id}"]`)
      const text = (label?.innerText || '') + (input.placeholder || '') + (input.getAttribute('aria-label') || '')
      return text.toLowerCase().includes('date') || text.toLowerCase().includes('heure') || text.toLowerCase().includes('time')
    })
    console.log('[VeilleIA] Inputs trouvés:', scheduleInputs.length)
    const dateInput = scheduleInputs[0] || await waitForElement(SELECTORS.dateInput, 5000)
    // Convertir YYYY-MM-DD en DD/MM/YYYY
    const [year, month, day] = post.scheduled_date.split('-')
    const formattedDate = `${day}/${month}/${year}`
    console.log('[VeilleIA] Date formatée:', formattedDate)
    dateInput.focus()
    dateInput.value = ''
    dateInput.value = formattedDate
    dateInput.dispatchEvent(new Event('input', { bubbles: true }))
    dateInput.dispatchEvent(new Event('change', { bubbles: true }))
    dateInput.dispatchEvent(new Event('blur', { bubbles: true }))
    await sleep(500)

    // 9. Remplir l'heure (format HH:MM)
    console.log('[VeilleIA] Sélection de l\'heure:', post.scheduled_time)
    const timeInput = scheduleInputs[1] || await waitForElement(SELECTORS.timeInput, 5000)
    timeInput.focus()
    timeInput.value = ''
    timeInput.value = post.scheduled_time
    timeInput.dispatchEvent(new Event('input', { bubbles: true }))
    timeInput.dispatchEvent(new Event('change', { bubbles: true }))
    timeInput.dispatchEvent(new Event('blur', { bubbles: true }))
    await sleep(500)

    // 10. Cliquer sur "Suivant" dans le modal de date/heure
    console.log('[VeilleIA] Clic sur Suivant (modal date/heure)...')
    let allBtns = Array.from(document.querySelectorAll('button'))
    let nextBtn = allBtns.find(btn =>
      btn.innerText.trim().toLowerCase() === 'suivant' ||
      btn.innerText.trim().toLowerCase() === 'next'
    )
    if (nextBtn) {
      nextBtn.click()
      await sleep(600)
    }

    // 11. Cliquer sur le bouton final "Programmer"
    console.log('[VeilleIA] Recherche du bouton Programmer...')

    // Attendre un peu que l'interface se stabilise
    await sleep(400)

    allBtns = Array.from(document.querySelectorAll('button'))

    // Chercher le bouton "Programmer" ou "Schedule"
    let programmerBtn = allBtns.find(btn => {
      const text = btn.innerText.trim().toLowerCase()
      return text === 'programmer' ||
             text === 'schedule' ||
             text === 'schedule post' ||
             text.includes('programmer') ||
             text.includes('schedule')
    })

    // Si pas trouvé, chercher un bouton primaire dans un modal
    if (!programmerBtn) {
      console.log('[VeilleIA] Bouton Programmer non trouvé par texte, recherche bouton primaire...')

      // Chercher dans les modals ouverts
      const modals = document.querySelectorAll('[role="dialog"], .artdeco-modal, .share-creation-state')
      modals.forEach(modal => {
        const primaryBtns = modal.querySelectorAll('button.artdeco-button--primary')
        primaryBtns.forEach(btn => {
          console.log('[VeilleIA] Bouton primaire dans modal:', btn.innerText.trim())
          if (!programmerBtn && !btn.disabled) {
            programmerBtn = btn
          }
        })
      })
    }

    // Dernier recours: chercher le bouton bleu/primaire qui n'est pas "Publier"
    if (!programmerBtn) {
      programmerBtn = document.querySelector('button.artdeco-button--primary:not([disabled])')
      if (programmerBtn) {
        console.log('[VeilleIA] Bouton primaire final trouvé:', programmerBtn.innerText.trim())
      }
    }

    if (programmerBtn) {
      console.log('[VeilleIA] Bouton Programmer trouvé:', programmerBtn.innerText.trim(), '- clic...')
      programmerBtn.click()
      await sleep(1000)

      // Vérifier si le modal s'est fermé (succès)
      const modalStillOpen = document.querySelector('[role="dialog"], .artdeco-modal')
      if (modalStillOpen) {
        console.log('[VeilleIA] Modal encore ouvert, tentative avec un autre bouton...')
        const finalBtn = modalStillOpen.querySelector('button.artdeco-button--primary:not([disabled])')
        if (finalBtn) {
          finalBtn.click()
          await sleep(800)
        }
      }
    } else {
      console.error('[VeilleIA] Aucun bouton Programmer trouvé!')
    }

    console.log('[VeilleIA] Post programmé avec succès!')

    return { success: true, postId: post.id, scheduled: true }

  } catch (error) {
    console.error('[VeilleIA] Erreur programmation:', error)
    return { success: false, error: error.message, postId: post.id }

  } finally {
    isPublishing = false
    currentPost = null
  }
}

/**
 * Publie un post immédiatement sur LinkedIn (fallback)
 */
async function publishPost(post) {
  if (isPublishing) {
    throw new Error('Publication déjà en cours')
  }

  isPublishing = true
  currentPost = post

  try {
    console.log('[VeilleIA] Début publication:', post.title)

    // 1. S'assurer qu'on est sur le feed LinkedIn
    if (!window.location.href.includes('linkedin.com/feed')) {
      window.location.href = 'https://www.linkedin.com/feed/'
      await sleep(3000)
    }

    // 2. Ouvrir le compositeur
    console.log('[VeilleIA] Ouverture compositeur...')
    const startButton = await waitForElement(SELECTORS.startPostButton)
    startButton.click()
    await sleep(2000)

    // 3. Attendre la zone de texte
    console.log('[VeilleIA] Attente zone de texte...')
    const textArea = await waitForElement(SELECTORS.postTextArea)

    // 4. Insérer le contenu
    console.log('[VeilleIA] Insertion du contenu...')
    await typeText(textArea, post.content)

    // 5. Upload de l'image si présente
    if (post.image_url || post.imageData) {
      console.log('[VeilleIA] Upload de l\'image...')
      await uploadImage(post.image_url || post.imageData)
    }

    // 6. Attendre un peu avant de publier
    await sleep(2000)

    // 7. Cliquer sur Publier
    console.log('[VeilleIA] Clic sur Publier...')
    const publishBtn = await waitForElement(SELECTORS.publishButton)

    // Vérifier que le bouton est activé
    if (publishBtn.disabled) {
      throw new Error('Bouton Publier désactivé')
    }

    publishBtn.click()

    // 8. Attendre la fin de la publication
    await sleep(3000)

    console.log('[VeilleIA] Publication terminée!')

    return { success: true, postId: post.id }

  } catch (error) {
    console.error('[VeilleIA] Erreur publication:', error)
    return { success: false, error: error.message, postId: post.id }

  } finally {
    isPublishing = false
    currentPost = null
  }
}

/**
 * Utilitaire sleep
 */
function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms))
}

/**
 * Écoute les messages du background script
 */
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  console.log('[VeilleIA] Message reçu:', message)

  // Programmer un post via le scheduler natif LinkedIn
  if (message.action === 'schedule') {
    schedulePostNative(message.post)
      .then(result => {
        sendResponse(result)
        chrome.runtime.sendMessage({
          action: 'scheduleResult',
          result
        })
      })
      .catch(error => {
        sendResponse({ success: false, error: error.message })
      })
    return true
  }

  // Publier immédiatement
  if (message.action === 'publish') {
    publishPost(message.post)
      .then(result => {
        sendResponse(result)
        // Notifier le background du résultat
        chrome.runtime.sendMessage({
          action: 'publishResult',
          result
        })
      })
      .catch(error => {
        sendResponse({ success: false, error: error.message })
      })
    return true // Indique une réponse asynchrone
  }

  if (message.action === 'checkReady') {
    sendResponse({
      ready: !isPublishing,
      isOnLinkedIn: window.location.href.includes('linkedin.com')
    })
    return true
  }

  if (message.action === 'getStatus') {
    sendResponse({
      isPublishing,
      currentPost: currentPost?.title || null
    })
    return true
  }
})

// Notifier que le content script est chargé
console.log('[VeilleIA] Content script LinkedIn chargé')
chrome.runtime.sendMessage({ action: 'contentScriptReady' })

// Détecter si l'app Tauri demande une programmation via URL
;(async function checkUrlForScheduleAction() {
  const urlParams = new URLSearchParams(window.location.search)
  const action = urlParams.get('veille_action')
  const postId = urlParams.get('post_id')

  if (action === 'schedule' && postId) {
    console.log('[VeilleIA] Programmation demandée via URL pour post:', postId)

    // Nettoyer l'URL (enlever les paramètres)
    const cleanUrl = window.location.origin + window.location.pathname
    window.history.replaceState({}, document.title, cleanUrl)

    // Attendre que la page soit bien chargée
    console.log('[VeilleIA] Attente chargement page...')
    await sleep(1000)
    console.log('[VeilleIA] Page chargée, demande post au background...')

    // Demander au background script de récupérer le post (évite la CSP de LinkedIn)
    try {
      const response = await chrome.runtime.sendMessage({
        action: 'getPostData',
        postId: postId
      })

      console.log('[VeilleIA] Réponse du background:', response)

      if (response.error) {
        console.error('[VeilleIA] Erreur:', response.error)
        showToast('Erreur: ' + response.error, 'error')
        return
      }

      const post = response.post
      if (post) {
        console.log('[VeilleIA] Post trouvé, lancement de la programmation...')
        // Utiliser imageBase64 au lieu de image_url
        if (post.imageBase64) {
          post.imageData = post.imageBase64
        }
        const result = await schedulePostNative(post)

        // Notifier le background du résultat pour mettre à jour le statut
        if (result.success) {
          await chrome.runtime.sendMessage({
            action: 'updatePostStatus',
            postId: postId,
            status: 'scheduled_linkedin'
          })
          showToast('Post programmé avec succès!', 'success')
        } else {
          showToast('Erreur: ' + result.error, 'error')
        }
      } else {
        console.error('[VeilleIA] Post non trouvé:', postId)
        showToast('Post non trouvé', 'error')
      }
    } catch (error) {
      console.error('[VeilleIA] Erreur:', error)
      showToast('Erreur de connexion', 'error')
    }
  }
})()

// Afficher un toast de notification
function showToast(message, type = 'info') {
  const toast = document.createElement('div')
  toast.className = `veille-ia-toast ${type}`
  toast.innerHTML = `<span>${message}</span>`
  document.body.appendChild(toast)

  setTimeout(() => {
    toast.classList.add('hiding')
    setTimeout(() => toast.remove(), 300)
  }, 4000)
}
