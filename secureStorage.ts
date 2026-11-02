/**
 * All auth token persistence goes through expo-secure-store (Keychain on
 * iOS, Keystore-backed EncryptedSharedPreferences on Android) — never
 * AsyncStorage, which is the React Native equivalent of the unencrypted
 * SharedPreferences gap found and fixed in ADR-0012 during the Flutter
 * phase. This time the lesson is applied from day one instead of found
 * later.
 */
import * as SecureStore from 'expo-secure-store';

const ACCESS_TOKEN_KEY = 'veya.access_token';
const REFRESH_TOKEN_KEY = 'veya.refresh_token';

export const secureStorage = {
  async getTokens(): Promise<{ access: string | null; refresh: string | null }> {
    const [access, refresh] = await Promise.all([
      SecureStore.getItemAsync(ACCESS_TOKEN_KEY),
      SecureStore.getItemAsync(REFRESH_TOKEN_KEY),
    ]);
    return { access, refresh };
  },

  async setTokens(access: string, refresh: string): Promise<void> {
    await Promise.all([
      SecureStore.setItemAsync(ACCESS_TOKEN_KEY, access),
      SecureStore.setItemAsync(REFRESH_TOKEN_KEY, refresh),
    ]);
  },

  async clearTokens(): Promise<void> {
    await Promise.all([
      SecureStore.deleteItemAsync(ACCESS_TOKEN_KEY),
      SecureStore.deleteItemAsync(REFRESH_TOKEN_KEY),
    ]);
  },
};
