import { classify, naiveMaterial, isMuteSacrifice, type ClassificationInput } from './noSweatClassify';
const material = new Map<string, number>();
const evaluate = (fen: string): number => {
  if (material.has(fen)) return material.get(fen)!;
  const value = naiveMaterial(fen);
  material.set(fen, value);
  if (material.size > 4000) material.delete(material.keys().next().value!);
  return value;
};
self.onmessage = (event: MessageEvent<ClassificationInput | { material: [string, string] }>) => {
  try {
    self.postMessage({
      result:
        'material' in event.data
          ? isMuteSacrifice(...event.data.material)
          : classify({ ...event.data, policy: 'mute-brilliant-v7' }, evaluate),
    });
  } catch (error) {
    self.postMessage({ error: String(error) });
  }
};
