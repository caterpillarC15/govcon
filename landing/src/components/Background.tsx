/**
 * Atmospheric backdrop. Pure CSS — no images, no JS, no animation —
 * so it has effectively zero perf cost and respects reduced-motion by default.
 * Pairs with .glass surfaces; provides the color/depth they refract.
 */
export default function Background() {
  return <div className="atmosphere" aria-hidden />
}
