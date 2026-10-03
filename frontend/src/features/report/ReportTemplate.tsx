import { forwardRef } from 'react';
import type { PredictResponse } from '@/api/types';
import { LogoMark } from '@/components/brand/Logo';
import { DISCLAIMER_TEXT } from '@/components/ui/Disclaimer';
import { LABELS, MODEL_META, TONE_HEX } from '@/utils/labels';
import { getReliability } from '@/utils/reliability';
import { dateTime, ms, pct } from '@/utils/format';

/** Off-screen, always-light A4 layout captured by html2canvas for the PDF. */
export const ReportTemplate = forwardRef<
  HTMLDivElement,
  { data: PredictResponse; threshold: number }
>(function ReportTemplate({ data, threshold }, ref) {
  return (
    <div
      ref={ref}
      className="force-light bg-white font-sans text-[13px] leading-relaxed text-[#1A2333]"
      style={{ width: 794, padding: 40 }}
    >
      <header className="flex items-center justify-between border-b-2 border-[#1E5AA8] pb-4">
        <div className="flex items-center gap-3">
          <LogoMark className="h-11 w-11" />
          <div>
            <p className="text-xl font-bold">PneumoScan AI</p>
            <p className="text-xs text-[#5B6678]">Chest X-ray analysis report · decision support</p>
          </div>
        </div>
        <div className="text-right text-xs text-[#5B6678]">
          <p>{dateTime(data.created_at)}</p>
          <p className="font-mono">ID {data.id.slice(0, 8)}</p>
        </div>
      </header>

      {data.is_mock && (
        <p className="mt-4 rounded-md border border-[#E0A800] bg-[#FFF8E1] px-3 py-2 text-xs text-[#856300]">
          Demo mode: results were produced by simulated (mock) models, not trained networks.
        </p>
      )}

      <section className="mt-5 grid grid-cols-2 gap-4">
        {data.results.map((r) => {
          const rel = getReliability(r, threshold);
          const s1 = LABELS[r.stage1.label];
          const s2 = r.stage2 ? LABELS[r.stage2.label] : null;
          return (
            <div key={r.model} className="rounded-lg border border-[#DDE4ED] p-4">
              <p className="text-xs font-semibold uppercase tracking-wider text-[#5B6678]">
                {MODEL_META[r.model].name}
              </p>
              <p className="mt-2 text-xs text-[#5B6678]">Stage 1 · Detection</p>
              <p className="text-2xl font-bold" style={{ color: TONE_HEX[s1.tone] }}>
                {s1.short}{' '}
                <span className="font-mono text-base text-[#1A2333]">
                  {pct(r.stage1.confidence)}
                </span>
              </p>
              {s2 && r.stage2 && (
                <>
                  <p className="mt-2 text-xs text-[#5B6678]">Stage 2 · Type</p>
                  <p className="text-lg font-bold" style={{ color: TONE_HEX[s2.tone] }}>
                    {s2.short}{' '}
                    <span className="font-mono text-sm text-[#1A2333]">
                      {pct(r.stage2.confidence)}
                    </span>
                  </p>
                </>
              )}
              <p className="mt-2 text-xs">
                <strong>Reliability:</strong> {rel.message} (threshold {pct(threshold, 0)})
              </p>
              <p className="text-xs">
                <strong>Probabilities:</strong>{' '}
                {Object.entries(r.class_probabilities)
                  .map(([k, v]) => `${LABELS[k as keyof typeof LABELS].text} ${pct(v ?? 0)}`)
                  .join(', ')}
              </p>
              {r.explanation && (
                <p className="text-xs">
                  <strong>Explanation:</strong> {r.explanation.description} Attention inside lung
                  region: {r.explanation.lung_attention_pct.toFixed(0)}%.
                </p>
              )}
              <p className="text-xs text-[#5B6678]">Inference time {ms(r.inference_ms)}</p>
            </div>
          );
        })}
      </section>

      {data.agreement && (
        <p
          className="mt-4 rounded-md px-3 py-2 text-sm font-semibold"
          style={{
            background: data.agreement.agree ? '#E8F6EF' : '#FFF8E1',
            color: data.agreement.agree ? '#16784F' : '#856300',
          }}
        >
          {data.agreement.agree
            ? 'Both models agree.'
            : 'Models disagree — expert review recommended.'}
        </p>
      )}

      <section className="mt-5">
        <p className="mb-2 text-xs font-semibold uppercase tracking-wider text-[#5B6678]">Images</p>
        <div className="grid grid-cols-3 gap-3">
          <figure>
            <img src={data.image_png} alt="" className="w-full rounded-md bg-black" />
            <figcaption className="mt-1 text-center text-[11px] text-[#5B6678]">
              Original
            </figcaption>
          </figure>
          {data.results.map((r) =>
            r.explanation ? (
              <figure key={r.model}>
                <div className="relative">
                  <img src={data.image_png} alt="" className="w-full rounded-md bg-black" />
                  <img
                    src={r.explanation.heatmap_png}
                    alt=""
                    className="absolute inset-0 h-full w-full rounded-md opacity-45"
                  />
                </div>
                <figcaption className="mt-1 text-center text-[11px] text-[#5B6678]">
                  Grad-CAM · {MODEL_META[r.model].short}
                </figcaption>
              </figure>
            ) : null,
          )}
        </div>
        <div className="mt-2 flex items-center gap-2 text-[10px] text-[#5B6678]">
          Low <span className="bg-jet h-2 w-32 rounded-full" /> High influence
        </div>
      </section>

      {data.validation.warnings.length > 0 && (
        <p className="mt-4 text-xs text-[#856300]">
          Image quality: {data.validation.warnings.join(' ')}
        </p>
      )}

      <section className="mt-5 space-y-2 border-t border-[#DDE4ED] pt-4 text-[11px] text-[#5B6678]">
        <p>
          <strong className="text-[#1A2333]">Disclaimer.</strong> {DISCLAIMER_TEXT}
        </p>
        <p>
          Viral vs bacterial distinction from X-ray alone is less reliable; confirm with clinical
          and laboratory tests.
        </p>
        <p>
          Image: {data.image.width}×{data.image.height} px, {data.image.format}. Uploaded images are
          processed in memory and metadata is stripped.
        </p>
      </section>
    </div>
  );
});
