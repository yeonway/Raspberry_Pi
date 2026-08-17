export type ProfileData = {
  id: string;
  name: string;
  shortDescription: string;
  detailedDescription?: string;
  imageUrl: string;
  genderLabel?: string;
  enabled: boolean;
  order: number;
};

const STORAGE_KEY = "zeta-profile-v2";

export function getSelectedProfileId(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(STORAGE_KEY);
}

export function setSelectedProfileId(id: string): void {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(STORAGE_KEY, id);
}

export function clearSelectedProfile(): void {
  if (typeof window === "undefined") return;
  window.localStorage.removeItem(STORAGE_KEY);
}

export function getSelectedProfile(profiles: ProfileData[]): ProfileData | undefined {
  const id = getSelectedProfileId();
  return profiles.find((p) => p.id === id);
}
