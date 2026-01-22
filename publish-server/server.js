/**
 * Veille IA - Publish Server
 * Serveur local qui expose les posts programmés à l'extension Chrome
 * et vérifie périodiquement s'il y a des posts à publier
 */

import express from 'express'
import cors from 'cors'
import cron from 'node-cron'
import fs from 'fs/promises'
import path from 'path'
import { fileURLToPath } from 'url'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)

const app = express()
const PORT = 3847

// Configuration
const CONFIG = {
  scheduledPostsPath: path.join(__dirname, '..', 'output', 'scheduled_posts.json'),
  projectPath: path.join(__dirname, '..')
}

// Middleware
app.use(cors())
app.use(express.json())

/**
 * Lit les posts programmés depuis le fichier JSON
 */
async function readScheduledPosts() {
  try {
    const content = await fs.readFile(CONFIG.scheduledPostsPath, 'utf-8')
    const data = JSON.parse(content)
    return data.posts || []
  } catch (error) {
    console.error('[Server] Erreur lecture posts:', error.message)
    return []
  }
}

/**
 * Sauvegarde les posts programmés
 */
async function saveScheduledPosts(posts) {
  try {
    const data = {
      posts,
      updated_at: new Date().toISOString()
    }
    await fs.writeFile(CONFIG.scheduledPostsPath, JSON.stringify(data, null, 2))
    console.log('[Server] Posts sauvegardés')
  } catch (error) {
    console.error('[Server] Erreur sauvegarde posts:', error.message)
    throw error
  }
}

// ========== API Routes ==========

/**
 * GET /api/scheduled-posts
 * Retourne tous les posts programmés
 */
app.get('/api/scheduled-posts', async (req, res) => {
  try {
    const posts = await readScheduledPosts()
    res.json({ posts, timestamp: new Date().toISOString() })
  } catch (error) {
    res.status(500).json({ error: error.message })
  }
})

/**
 * GET /api/scheduled-posts/pending
 * Retourne les posts qui doivent être publiés maintenant
 */
app.get('/api/scheduled-posts/pending', async (req, res) => {
  try {
    const posts = await readScheduledPosts()
    const now = new Date()

    const pendingPosts = posts.filter(post => {
      if (post.status !== 'scheduled') return false

      const scheduledDate = new Date(`${post.scheduled_date}T${post.scheduled_time}:00`)
      const diff = now - scheduledDate

      // Le post doit être publié si l'heure est passée (avec 5 min de marge)
      return diff >= 0 && diff < 5 * 60 * 1000
    })

    res.json({ posts: pendingPosts, timestamp: new Date().toISOString() })
  } catch (error) {
    res.status(500).json({ error: error.message })
  }
})

/**
 * PATCH /api/scheduled-posts/:id
 * Met à jour le statut d'un post
 */
app.patch('/api/scheduled-posts/:id', async (req, res) => {
  try {
    const { id } = req.params
    const { status, error, published_at } = req.body

    const posts = await readScheduledPosts()
    const postIndex = posts.findIndex(p => p.id === id)

    if (postIndex === -1) {
      return res.status(404).json({ error: 'Post non trouvé' })
    }

    posts[postIndex] = {
      ...posts[postIndex],
      status,
      ...(error && { error }),
      ...(published_at && { published_at })
    }

    await saveScheduledPosts(posts)

    res.json({ success: true, post: posts[postIndex] })
  } catch (error) {
    res.status(500).json({ error: error.message })
  }
})

/**
 * DELETE /api/scheduled-posts/:id
 * Supprime un post programmé
 */
app.delete('/api/scheduled-posts/:id', async (req, res) => {
  try {
    const { id } = req.params
    const posts = await readScheduledPosts()
    const filteredPosts = posts.filter(p => p.id !== id)

    if (filteredPosts.length === posts.length) {
      return res.status(404).json({ error: 'Post non trouvé' })
    }

    await saveScheduledPosts(filteredPosts)

    res.json({ success: true })
  } catch (error) {
    res.status(500).json({ error: error.message })
  }
})

/**
 * GET /api/image
 * Sert une image depuis le projet
 */
app.get('/api/image', async (req, res) => {
  try {
    const { path: imagePath } = req.query

    if (!imagePath) {
      return res.status(400).json({ error: 'Path manquant' })
    }

    // Construire le chemin complet
    const fullPath = imagePath.startsWith('/')
      ? imagePath
      : path.join(CONFIG.projectPath, imagePath)

    // Vérifier que le fichier existe
    await fs.access(fullPath)

    // Lire et envoyer l'image
    const imageBuffer = await fs.readFile(fullPath)
    const ext = path.extname(fullPath).toLowerCase()

    const mimeTypes = {
      '.png': 'image/png',
      '.jpg': 'image/jpeg',
      '.jpeg': 'image/jpeg',
      '.gif': 'image/gif',
      '.webp': 'image/webp'
    }

    res.setHeader('Content-Type', mimeTypes[ext] || 'image/png')
    res.send(imageBuffer)
  } catch (error) {
    console.error('[Server] Erreur image:', error.message)
    res.status(404).json({ error: 'Image non trouvée' })
  }
})

/**
 * GET /api/health
 * Vérifie que le serveur est en marche
 */
app.get('/api/health', (req, res) => {
  res.json({
    status: 'ok',
    timestamp: new Date().toISOString(),
    uptime: process.uptime()
  })
})

// ========== Cron Job ==========

/**
 * Vérifie toutes les minutes s'il y a des posts à publier
 * et log l'information (l'extension Chrome fait la publication)
 */
cron.schedule('* * * * *', async () => {
  try {
    const posts = await readScheduledPosts()
    const now = new Date()

    const pendingPosts = posts.filter(post => {
      if (post.status !== 'scheduled') return false

      const scheduledDate = new Date(`${post.scheduled_date}T${post.scheduled_time}:00`)
      const diff = now - scheduledDate

      return diff >= 0 && diff < 2 * 60 * 1000 // 2 minutes de fenêtre
    })

    if (pendingPosts.length > 0) {
      console.log(`[Cron] ${pendingPosts.length} post(s) à publier:`)
      pendingPosts.forEach(p => {
        console.log(`  - ${p.title} (${p.scheduled_date} ${p.scheduled_time})`)
      })
    }
  } catch (error) {
    console.error('[Cron] Erreur:', error.message)
  }
})

// ========== Démarrage ==========

app.listen(PORT, () => {
  console.log(`
╔════════════════════════════════════════════════════════╗
║     Veille IA - Publish Server                         ║
╠════════════════════════════════════════════════════════╣
║  Port: ${PORT}                                           ║
║  API: http://localhost:${PORT}/api/scheduled-posts       ║
║                                                        ║
║  Cron actif: vérifie chaque minute                     ║
╚════════════════════════════════════════════════════════╝
  `)
})
