import type { ReactNode } from 'react';
import {
  ArrowRight,
  BookOpen,
  Database,
  Eye,
  GraduationCap,
  Network,
  ShieldAlert,
  Users,
} from 'lucide-react';
import { PageHeader } from '@/components/ui/PageHeader';
import { Card, CardHeader } from '@/components/ui/Card';
import { Disclaimer } from '@/components/ui/Disclaimer';
import { PROJECT } from '@/config/project';
import { cn } from '@/utils/cn';

interface Block {
  label: string;
  sub?: string;
  highlight?: boolean;
}

function FlowDiagram({ blocks, caption }: { blocks: Block[]; caption: string }) {
  return (
    <figure>
      <ol className="flex flex-wrap items-center gap-y-3" aria-label={caption}>
        {blocks.map((b, i) => (
          <li key={b.label + i} className="flex items-center">
            <div
              className={cn(
                'rounded-xl border px-3 py-2 text-center',
                b.highlight
                  ? 'border-accent bg-accent/10 shadow-glow'
                  : 'border-border bg-surface-2',
              )}
            >
              <p className="text-sm font-semibold leading-tight">{b.label}</p>
              {b.sub && <p className="num mt-0.5 text-[11px] text-ink-muted">{b.sub}</p>}
            </div>
            {i < blocks.length - 1 && (
              <ArrowRight className="mx-1.5 h-4 w-4 shrink-0 text-ink-muted" aria-hidden />
            )}
          </li>
        ))}
      </ol>
      <figcaption className="mt-3 text-xs text-ink-muted">{caption}</figcaption>
    </figure>
  );
}

function Section({
  icon,
  title,
  children,
}: {
  icon: ReactNode;
  title: string;
  children: ReactNode;
}) {
  return (
    <Card className="p-5 sm:p-6">
      <CardHeader icon={icon} title={title} className="mb-4" />
      <div className="space-y-3 text-ink [&_p]:leading-relaxed">{children}</div>
    </Card>
  );
}

export function AboutPage() {
  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Project"
        title={`About ${PROJECT.name}`}
        description={PROJECT.subtitle}
      />

      <Section icon={<BookOpen className="h-5 w-5" />} title="Overview">
        <p>
          PneumoScan AI is a decision-support system that screens chest X-rays (CXR) for pneumonia
          and, when pneumonia is found, estimates whether the radiographic pattern looks more
          bacterial or viral. Every prediction comes with a calibrated confidence, a reliability
          flag and a Grad-CAM heatmap so clinicians can see <em>why</em> the model decided what it
          did.
        </p>
        <p>
          Two architecture families are trained under identical settings for a fair comparison: a
          convolutional network (DenseNet121) and a vision transformer (Swin-Tiny). They can be run
          individually or side by side.
        </p>
        <FlowDiagram
          caption="Inference pipeline. Stage 2 only runs when Stage 1 predicts pneumonia. A single 3-class model is also supported via configuration."
          blocks={[
            { label: 'Upload', sub: 'PNG/JPEG/DICOM' },
            { label: 'Validate', sub: 'is it a CXR?' },
            { label: 'Preprocess', sub: '224×224 · CLAHE' },
            { label: 'Stage 1', sub: 'Normal / Pneumonia', highlight: true },
            { label: 'Stage 2', sub: 'Bacterial / Viral', highlight: true },
            { label: 'Calibrate', sub: 'temperature' },
            { label: 'Grad-CAM', sub: 'explain' },
          ]}
        />
      </Section>

      <Section icon={<Database className="h-5 w-5" />} title="Datasets">
        <p>
          <strong>Primary:</strong> Kermany et al., “Chest X-Ray Images (Pneumonia)” — 5,856
          pediatric anterior-posterior CXRs from Guangzhou Women and Children's Medical Center,
          labelled Normal, Bacterial or Viral (subtype parsed from filenames). Patients were aged
          1–5 and all images come from a single hospital.
        </p>
        <p>
          Data are re-split <strong>70 / 15 / 15</strong> (train / validation / test), grouped by
          patient ID so no patient appears in more than one split. The original 16-image Kaggle
          validation folder is not used.
        </p>
        <p>
          <strong>External validation (Stage 1 only):</strong> RSNA Pneumonia Detection Challenge
          (adult CXRs, derived from NIH ChestX-ray14), optionally other public sets. These lack
          viral/bacterial labels, so only detection is evaluated, and the performance drop versus
          the internal test set is reported.
        </p>
      </Section>

      <Section icon={<Network className="h-5 w-5" />} title="Model architectures">
        <div className="space-y-6">
          <div>
            <h3 className="mb-2 font-semibold">DenseNet121 (CNN)</h3>
            <p className="mb-3 text-sm text-ink-muted">
              Each layer receives the feature maps of all preceding layers in its block, encouraging
              feature reuse with few parameters (~8M). ImageNet-pretrained, classifier replaced with
              a 2-class head.
            </p>
            <FlowDiagram
              caption="Grad-CAM target: output of the last dense block (features.denseblock4)."
              blocks={[
                { label: 'Conv + Pool', sub: '7×7, s2' },
                { label: 'Dense Block 1', sub: '×6' },
                { label: 'Transition' },
                { label: 'Dense Block 2', sub: '×12' },
                { label: 'Transition' },
                { label: 'Dense Block 3', sub: '×24' },
                { label: 'Transition' },
                { label: 'Dense Block 4', sub: '×16 · 7×7×1024', highlight: true },
                { label: 'GAP + FC', sub: '2 classes' },
              ]}
            />
          </div>
          <div>
            <h3 className="mb-2 font-semibold">Swin Transformer — Tiny (ViT)</h3>
            <p className="mb-3 text-sm text-ink-muted">
              Self-attention inside shifted local windows, with patch merging building a CNN-like
              feature hierarchy (~28M parameters). Model:{' '}
              <code className="num">swin_tiny_patch4_window7_224</code> from timm.
            </p>
            <FlowDiagram
              caption="Grad-CAM target: the final LayerNorm; a reshape transform turns the 7×7 token grid back into a 2-D feature map."
              blocks={[
                { label: 'Patch Partition', sub: '4×4 → 56×56' },
                { label: 'Stage 1', sub: 'W/SW-MSA ×2' },
                { label: 'Stage 2', sub: 'merge · ×2' },
                { label: 'Stage 3', sub: 'merge · ×6' },
                { label: 'Stage 4', sub: 'merge · ×2' },
                { label: 'LayerNorm', sub: '7×7×768', highlight: true },
                { label: 'GAP + FC', sub: '2 classes' },
              ]}
            />
          </div>
        </div>
      </Section>

      <Section icon={<Eye className="h-5 w-5" />} title="Grad-CAM explanations">
        <p>
          Gradient-weighted Class Activation Mapping takes the gradient of the predicted class score
          with respect to a late feature map, averages it per channel to get importance weights, and
          forms a weighted sum of the channels. After a ReLU and upsampling, this gives a coarse
          heatmap of the regions that most increased the class score.
        </p>
        <p>
          PneumoScan summarises the heatmap in words (e.g. “lower right lung”) using the
          radiological convention — the patient's right appears on the left of the image — and
          reports how much of the attention falls inside an estimated lung mask. Attention outside
          the lungs (text markers, devices, borders) suggests the model may be relying on shortcuts.
        </p>
      </Section>

      <Section icon={<ShieldAlert className="h-5 w-5" />} title="Limitations & ethics">
        <ul className="list-disc space-y-2 pl-5">
          <li>
            Trained on pediatric images from a single hospital — performance on adults, other
            scanners and other populations is expected to drop (see External Validation).
          </li>
          <li>
            Distinguishing viral from bacterial pneumonia on X-ray alone is inherently uncertain; it
            must be confirmed with clinical findings and laboratory tests.
          </li>
          <li>
            Grad-CAM is coarse (7×7 resolution before upsampling) and shows correlation, not
            causation.
          </li>
          <li>
            Calibrated probabilities are calibrated on the internal validation set and may not
            transfer to new sites.
          </li>
          <li>
            Testing with real patient X-rays must only be done with informed consent and appropriate
            institutional / ethics approval. Images are processed in memory, metadata is stripped
            and DICOM identifiers are removed.
          </li>
          <li>This tool is not a medical device and has not been clinically validated.</li>
        </ul>
      </Section>

      <Section icon={<Users className="h-5 w-5" />} title="Team">
        <div className="grid gap-3 sm:grid-cols-2">
          {PROJECT.team.map((m) => (
            <div key={m.name} className="rounded-xl bg-surface-2 p-4">
              <p className="font-semibold">{m.name}</p>
              <p className="text-sm text-ink-muted">{m.role}</p>
            </div>
          ))}
        </div>
        <div className="flex items-center gap-3 rounded-xl border border-border p-4">
          <GraduationCap className="h-5 w-5 text-primary-text" aria-hidden />
          <div>
            <p className="font-semibold">{PROJECT.guide.name}</p>
            <p className="text-sm text-ink-muted">
              {PROJECT.guide.title} · {PROJECT.institution} · {PROJECT.academicYear}
            </p>
          </div>
        </div>
      </Section>

      <Disclaimer />
    </div>
  );
}
