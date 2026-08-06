import 'package:file_picker/file_picker.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../data/models/document.dart';
import '../data/repositories.dart';
import 'core_providers.dart';

final documentsRepositoryProvider = Provider<DocumentsRepository>((ref) {
  return DocumentsRepository(ref.watch(apiClientProvider));
});

final samplesProvider = FutureProvider<List<SampleInfo>>((ref) {
  return ref.watch(documentsRepositoryProvider).fetchSamples();
});

final documentStatusFilterProvider = StateProvider<String?>((ref) => 'needs_review');

final documentsListProvider = FutureProvider.autoDispose<List<DocumentSummary>>((ref) {
  final status = ref.watch(documentStatusFilterProvider);
  return ref.watch(documentsRepositoryProvider).fetchDocuments(status: status);
});

final selectedDocumentIdProvider = StateProvider<int?>((ref) => null);

final documentDetailProvider = FutureProvider.autoDispose<DocumentDetail?>((ref) {
  final id = ref.watch(selectedDocumentIdProvider);
  if (id == null) return Future.value(null);
  return ref.watch(documentsRepositoryProvider).fetchDocument(id);
});

enum UploadItemStatus { uploading, done, error }

class UploadItem {
  const UploadItem({required this.filename, required this.status, this.error});
  final String filename;
  final UploadItemStatus status;
  final String? error;

  UploadItem copyWith({UploadItemStatus? status, String? error}) => UploadItem(
    filename: filename,
    status: status ?? this.status,
    error: error ?? this.error,
  );
}

class BulkUploadState {
  const BulkUploadState({this.items = const []});
  final List<UploadItem> items;

  int get doneCount => items.where((i) => i.status == UploadItemStatus.done).length;
  int get errorCount => items.where((i) => i.status == UploadItemStatus.error).length;
  bool get inProgress => items.any((i) => i.status == UploadItemStatus.uploading);
}

class BulkUploadNotifier extends Notifier<BulkUploadState> {
  @override
  BulkUploadState build() => const BulkUploadState();

  Future<void> uploadFiles(List<PlatformFile> files) async {
    state = BulkUploadState(
      items: [
        for (final f in files) UploadItem(filename: f.name, status: UploadItemStatus.uploading),
      ],
    );
    final repo = ref.read(documentsRepositoryProvider);

    for (var i = 0; i < files.length; i++) {
      try {
        await repo.upload([files[i]]);
        _update(i, UploadItemStatus.done);
      } catch (e) {
        _update(i, UploadItemStatus.error, error: '$e');
      }
    }
    ref.invalidate(documentsListProvider);
  }

  void _update(int index, UploadItemStatus status, {String? error}) {
    final items = [...state.items];
    items[index] = items[index].copyWith(status: status, error: error);
    state = BulkUploadState(items: items);
  }

  void clear() => state = const BulkUploadState();
}

final bulkUploadProvider = NotifierProvider<BulkUploadNotifier, BulkUploadState>(
  BulkUploadNotifier.new,
);
