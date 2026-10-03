import { getReliability } from '@/utils/reliability';
import { makeResult } from './fixtures';

describe('getReliability', () => {
  it('is high when every stage clears the threshold', () => {
    expect(getReliability(makeResult(), 0.75).level).toBe('high');
  });

  it('is low when any stage is below the threshold', () => {
    const r = getReliability(makeResult(), 0.85);
    expect(r.level).toBe('low');
    expect(r.message).toMatch(/expert review/);
  });

  it('only considers stage 1 for a normal result', () => {
    const normal = makeResult({
      stage1: {
        label: 'NORMAL',
        confidence: 0.9,
        probabilities: { NORMAL: 0.9, PNEUMONIA: 0.1 },
        temperature: 1,
      },
      stage2: null,
      final_label: 'NORMAL',
    });
    expect(getReliability(normal, 0.85).level).toBe('high');
  });
});
