import * as ImagePicker from 'expo-image-picker';
import { PickedImage } from './api';

export async function pickImage(options: { square?: boolean } = {}): Promise<PickedImage | null> {
  const perm = await ImagePicker.requestMediaLibraryPermissionsAsync();
  if (!perm.granted) throw new Error('Photo access was denied. Enable it in Settings to choose a photo.');
  const result = await ImagePicker.launchImageLibraryAsync({
    mediaTypes: ImagePicker.MediaTypeOptions.Images,
    quality: 0.8,
    allowsEditing: !!options.square,
    aspect: options.square ? [1, 1] : undefined,
  });
  const asset = result.canceled ? undefined : result.assets[0];
  if (!asset) return null;
  return { uri: asset.uri, mimeType: asset.mimeType, fileName: asset.fileName, fileSize: asset.fileSize };
}
