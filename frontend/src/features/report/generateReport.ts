/** Captures the report template with html2canvas and paginates it into an A4 PDF. */
export async function generateReportPdf(element: HTMLElement, filename: string): Promise<void> {
  const [{ default: html2canvas }, { jsPDF }] = await Promise.all([
    import('html2canvas'),
    import('jspdf'),
  ]);
  const canvas = await html2canvas(element, {
    scale: 2,
    backgroundColor: '#ffffff',
    useCORS: true,
    logging: false,
  });

  const pdf = new jsPDF({ unit: 'mm', format: 'a4', orientation: 'portrait' });
  const pageW = pdf.internal.pageSize.getWidth();
  const pageH = pdf.internal.pageSize.getHeight();
  const pxPerMm = canvas.width / pageW;
  const pagePx = Math.floor(pageH * pxPerMm);

  for (let y = 0, page = 0; y < canvas.height; y += pagePx, page++) {
    const slice = document.createElement('canvas');
    slice.width = canvas.width;
    slice.height = Math.min(pagePx, canvas.height - y);
    slice.getContext('2d')!.drawImage(canvas, 0, -y);
    if (page > 0) pdf.addPage();
    pdf.addImage(slice.toDataURL('image/jpeg', 0.92), 'JPEG', 0, 0, pageW, slice.height / pxPerMm);
  }
  pdf.save(filename);
}
