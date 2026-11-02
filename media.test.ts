import { MAX_IMAGE_BYTES, validatePickedImage } from '../media/api';

describe('validatePickedImage', () => {
  it('accepts jpeg/png/webp under the limit', () => {
    for (const t of ['image/jpeg', 'image/png', 'image/webp'])
      expect(validatePickedImage({ uri: 'x', mimeType: t, fileSize: 1000 })).toBeNull();
  });
  it('accepts when type/size are unknown (server decides)', () => expect(validatePickedImage({ uri: 'x' })).toBeNull());
  it('rejects gif / svg / heic', () => {
    for (const t of ['image/gif', 'image/svg+xml', 'image/heic'])
      expect(validatePickedImage({ uri: 'x', mimeType: t })).not.toBeNull();
  });
  it('rejects over the size limit, accepts exactly at it', () => {
    expect(validatePickedImage({ uri: 'x', fileSize: MAX_IMAGE_BYTES + 1 })).not.toBeNull();
    expect(validatePickedImage({ uri: 'x', fileSize: MAX_IMAGE_BYTES })).toBeNull();
  });
});
