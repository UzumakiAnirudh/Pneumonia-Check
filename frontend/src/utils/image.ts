/** Browser image helpers (file info, thumbnails, jet colormap). */

export const ACCEPTED_IMAGE_TYPES = {
  'image/png': ['.png'],
  'image/jpeg': ['.jpg', '.jpeg'],
  'application/dicom': ['.dcm', '.dicom'],
} as const;

export const MAX_UPLOAD_BYTES = 25 * 1024 * 1024;

export function isDicomFile(file: File): boolean {
  return /\.(dcm|dicom)$/i.test(file.name) || file.type === 'application/dicom';
}

export function loadImage(src: string): Promise<HTMLImageElement> {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.onload = () => resolve(img);
    img.onerror = () => reject(new Error('Could not decode image'));
    img.src = src;
  });
}

export async function loadImageFromFile(file: File): Promise<HTMLImageElement> {
  const url = URL.createObjectURL(file);
  try {
    return await loadImage(url);
  } finally {
    // Safe to revoke once decoded.
    setTimeout(() => URL.revokeObjectURL(url), 0);
  }
}

export async function getImageDimensions(
  file: File,
): Promise<{ width: number; height: number } | null> {
  if (isDicomFile(file)) return null;
  try {
    const img = await loadImageFromFile(file);
    return { width: img.naturalWidth, height: img.naturalHeight };
  } catch {
    return null;
  }
}

/** Draw an image scaled so its long side is at most `maxSide`. */
export function drawScaled(
  img: CanvasImageSource & { width: number; height: number },
  maxSide: number,
  grayscale = false,
): HTMLCanvasElement {
  const scale = Math.min(1, maxSide / Math.max(img.width, img.height));
  const canvas = document.createElement('canvas');
  canvas.width = Math.max(1, Math.round(img.width * scale));
  canvas.height = Math.max(1, Math.round(img.height * scale));
  const ctx = canvas.getContext('2d')!;
  if (grayscale) ctx.filter = 'grayscale(1)';
  ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
  return canvas;
}

/** Jet colormap, matching OpenCV's COLORMAP_JET closely. Input 0–1, output RGB 0–255. */
export function jet(v: number): [number, number, number] {
  const x = Math.min(1, Math.max(0, v));
  const c = (t: number) => Math.round(255 * Math.min(1, Math.max(0, 1.5 - Math.abs(4 * x - t))));
  return [c(3), c(2), c(1)];
}

export async function dataUrlToFile(dataUrl: string, name: string): Promise<File> {
  const blob = await (await fetch(dataUrl)).blob();
  return new File([blob], name, { type: blob.type });
}
