/**
 * Veille IA - Popup Script
 */

document.addEventListener('DOMContentLoaded', async () => {
  const statusDot = document.getElementById('statusDot')
  const statusText = document.getElementById('statusText')
  const postList = document.getElementById('postList')
  const refreshBtn = document.getElementById('refreshBtn')
  const openLinkedInBtn = document.getElementById('openLinkedInBtn')

  // Charger les données
  async function loadData() {
    try {
      // Demander le statut au background
      const status = await chrome.runtime.sendMessage({ action: 'getStatus' })

      // Mettre à jour l'indicateur de connexion
      if (status.isConnected) {
        statusDot.classList.remove('disconnected')
        statusDot.classList.add('connected')
        statusText.textContent = `Connecté • ${status.scheduledCount} post(s) programmé(s)`
      } else {
        statusDot.classList.remove('connected')
        statusDot.classList.add('disconnected')
        statusText.textContent = 'Déconnecté de l\'API locale'
      }

      // Charger les posts
      const data = await chrome.runtime.sendMessage({ action: 'getScheduledPosts' })
      renderPosts(data.posts || [])

    } catch (error) {
      console.error('Erreur chargement:', error)
      statusDot.classList.remove('connected')
      statusDot.classList.add('disconnected')
      statusText.textContent = 'Erreur de connexion'
    }
  }

  // Afficher les posts
  function renderPosts(posts) {
    if (!posts || posts.length === 0) {
      postList.innerHTML = `
        <div class="empty-state">
          <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <rect x="3" y="4" width="18" height="18" rx="2" ry="2"/>
            <line x1="16" y1="2" x2="16" y2="6"/>
            <line x1="8" y1="2" x2="8" y2="6"/>
            <line x1="3" y1="10" x2="21" y2="10"/>
          </svg>
          <div>Aucun post programmé</div>
        </div>
      `
      return
    }

    // Trier par date
    const sortedPosts = [...posts].sort((a, b) => {
      const dateA = new Date(`${a.scheduled_date}T${a.scheduled_time}`)
      const dateB = new Date(`${b.scheduled_date}T${b.scheduled_time}`)
      return dateA - dateB
    })

    // Afficher les 5 prochains
    const upcomingPosts = sortedPosts
      .filter(p => p.status === 'scheduled')
      .slice(0, 5)

    if (upcomingPosts.length === 0) {
      postList.innerHTML = `
        <div class="empty-state">
          <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="20 6 9 17 4 12"/>
          </svg>
          <div>Tous les posts ont été publiés</div>
        </div>
      `
      return
    }

    postList.innerHTML = upcomingPosts.map(post => {
      const date = new Date(`${post.scheduled_date}T${post.scheduled_time}`)
      const dateStr = date.toLocaleDateString('fr-FR', {
        weekday: 'short',
        day: 'numeric',
        month: 'short'
      })
      const timeStr = post.scheduled_time

      return `
        <div class="post-item">
          <div class="post-info">
            <div class="post-title">${escapeHtml(post.title)}</div>
            <div class="post-time">${dateStr} à ${timeStr}</div>
          </div>
          <span class="post-status ${post.status}">${getStatusLabel(post.status)}</span>
        </div>
      `
    }).join('')
  }

  function getStatusLabel(status) {
    switch (status) {
      case 'scheduled': return 'Programmé'
      case 'published': return 'Publié'
      case 'failed': return 'Échoué'
      default: return status
    }
  }

  function escapeHtml(text) {
    const div = document.createElement('div')
    div.textContent = text
    return div.innerHTML
  }

  // Événements
  refreshBtn.addEventListener('click', async () => {
    refreshBtn.textContent = 'Actualisation...'
    refreshBtn.disabled = true

    await chrome.runtime.sendMessage({ action: 'forceCheck' })
    await loadData()

    refreshBtn.textContent = 'Actualiser'
    refreshBtn.disabled = false
  })

  openLinkedInBtn.addEventListener('click', () => {
    chrome.tabs.create({ url: 'https://www.linkedin.com/feed/' })
  })

  // Charger les données au démarrage
  await loadData()
})
