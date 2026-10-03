import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { UploadZone } from '@/features/upload/UploadZone';

function drop(input: HTMLElement, file: File) {
  fireEvent.drop(input, {
    dataTransfer: {
      files: [file],
      items: [{ kind: 'file', type: file.type, getAsFile: () => file }],
      types: ['Files'],
    },
  });
}

describe('UploadZone', () => {
  it('accepts a PNG', async () => {
    const onFile = vi.fn();
    render(<UploadZone onFile={onFile} />);
    const file = new File([new Uint8Array([137, 80, 78, 71])], 'cxr.png', { type: 'image/png' });
    drop(screen.getByLabelText('Upload a chest X-ray image').parentElement!, file);
    await waitFor(() => expect(onFile).toHaveBeenCalledWith(file));
  });

  it('rejects unsupported types with a message', async () => {
    const onFile = vi.fn();
    render(<UploadZone onFile={onFile} />);
    const file = new File(['hello'], 'notes.txt', { type: 'text/plain' });
    drop(screen.getByLabelText('Upload a chest X-ray image').parentElement!, file);
    expect(await screen.findByRole('alert')).toHaveTextContent(/Unsupported file type/);
    expect(onFile).not.toHaveBeenCalled();
  });
});
