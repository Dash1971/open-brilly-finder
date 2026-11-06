import type { ClassificationInput, ClassificationResult } from './noSweatClassify';
export class ClassifierClient {
  private worker?: Worker;
  private cancel?: () => void;
  constructor(private readonly create: () => Worker) {}
  classify(input: ClassificationInput, signal: AbortSignal): Promise<ClassificationResult> {
    return this.request(input, signal);
  }
  sacrifice(before: string, after: string, signal: AbortSignal): Promise<boolean> {
    return this.request({ material: [before, after] }, signal);
  }
  private request<T>(input: unknown, signal: AbortSignal): Promise<T> {
    if (signal.aborted) return Promise.reject(new Error('Cancelled'));
    if (this.cancel) return Promise.reject(new Error('Classifier is busy'));
    const worker = (this.worker ??= this.create());
    return new Promise((resolve, reject) => {
      const finish = (error?: Error, result?: T) => {
        clearTimeout(timer);
        signal.removeEventListener('abort', aborted);
        this.cancel = undefined;
        worker.onmessage = null;
        worker.onerror = null;
        if (error) {
          worker.terminate();
          if (this.worker === worker) this.worker = undefined;
          reject(error);
        } else resolve(result!);
      };
      const aborted = () => finish(new Error('Cancelled'));
      const timer = setTimeout(
        () => finish(new Error('Capture search timed out; classification unavailable')),
        10000,
      );
      this.cancel = aborted;
      signal.addEventListener('abort', aborted, { once: true });
      worker.onmessage = ({ data }) => {
        if (this.worker === worker) finish(data.error ? new Error(data.error) : undefined, data.result);
      };
      worker.onerror = () => finish(new Error('Classification worker failed'));
      try {
        worker.postMessage(input);
      } catch (error) {
        finish(new Error(String(error)));
      }
    });
  }
  release(): void {
    this.cancel?.();
    this.worker?.terminate();
    this.worker = undefined;
  }
}
