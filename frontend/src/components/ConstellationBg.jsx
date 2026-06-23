import { useRef, useEffect } from 'react'

// Constellatie-achtergrond (SureSync-stijl, paars netwerk). Geen externe assets.
export default function ConstellationBg({ color = '#7344F3', style = {} }) {
  const ref = useRef(null)
  useEffect(() => {
    const canvas = ref.current; if (!canvas) return
    const ctx = canvas.getContext('2d')
    const DPR = Math.min(window.devicePixelRatio || 1, 2)
    let raf, W = 0, H = 0, pts = []
    const resize = () => {
      const r = canvas.parentElement.getBoundingClientRect()
      W = r.width; H = r.height
      canvas.width = W * DPR; canvas.height = H * DPR
      ctx.setTransform(DPR, 0, 0, DPR, 0, 0)
      const n = Math.max(16, Math.round((W * H) / 24000))
      pts = Array.from({ length: n }, () => ({
        x: Math.random() * W, y: Math.random() * H,
        vx: (Math.random() - 0.5) * 0.22, vy: (Math.random() - 0.5) * 0.22,
        r: Math.random() * 1.6 + 0.6,
      }))
    }
    const step = () => {
      ctx.clearRect(0, 0, W, H)
      for (const p of pts) { p.x += p.vx; p.y += p.vy
        if (p.x < 0 || p.x > W) p.vx *= -1; if (p.y < 0 || p.y > H) p.vy *= -1 }
      for (let i = 0; i < pts.length; i++) for (let j = i + 1; j < pts.length; j++) {
        const a = pts[i], b = pts[j], d = Math.hypot(a.x - b.x, a.y - b.y)
        if (d < 140) { ctx.globalAlpha = (1 - d / 140) * 0.45; ctx.strokeStyle = color; ctx.lineWidth = 1
          ctx.beginPath(); ctx.moveTo(a.x, a.y); ctx.lineTo(b.x, b.y); ctx.stroke() }
      }
      ctx.shadowColor = color; ctx.shadowBlur = 8
      for (const p of pts) { ctx.globalAlpha = 0.9; ctx.fillStyle = color
        ctx.beginPath(); ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2); ctx.fill() }
      ctx.shadowBlur = 0; ctx.globalAlpha = 1
      raf = requestAnimationFrame(step)
    }
    resize(); step()
    window.addEventListener('resize', resize)
    return () => { cancelAnimationFrame(raf); window.removeEventListener('resize', resize) }
  }, [color])
  return <canvas ref={ref} aria-hidden="true" style={{ position: 'absolute', inset: 0, width: '100%', height: '100%', pointerEvents: 'none', zIndex: 0, ...style }} />
}
