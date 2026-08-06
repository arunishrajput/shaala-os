import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/skeleton.dart';
import '../../core/theme.dart';
import '../../data/models/document.dart';
import '../../providers/documents_providers.dart';
import 'review_panel.dart';

class DocumentsScreen extends ConsumerWidget {
  const DocumentsScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final selectedId = ref.watch(selectedDocumentIdProvider);

    return Row(
      children: [
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: const [
              _Header(),
              _BulkUploadBanner(),
              Expanded(child: Padding(padding: EdgeInsets.all(16), child: _DocumentList())),
            ],
          ),
        ),
        if (selectedId != null) const ReviewPanel(),
      ],
    );
  }
}

class _Header extends ConsumerWidget {
  const _Header();

  Future<void> _pickAndUpload(WidgetRef ref, {required bool allowMultiple}) async {
    final result = await FilePicker.platform.pickFiles(
      type: FileType.image,
      allowMultiple: allowMultiple,
      withData: true,
    );
    if (result == null || result.files.isEmpty) return;
    await ref.read(bulkUploadProvider.notifier).uploadFiles(result.files);
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final samplesAsync = ref.watch(samplesProvider);
    final filter = ref.watch(documentStatusFilterProvider);

    return Padding(
      padding: const EdgeInsets.fromLTRB(24, 24, 24, 0),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Text('Documents', style: Theme.of(context).textTheme.headlineSmall),
              const Spacer(),
              OutlinedButton.icon(
                onPressed: () => _pickAndUpload(ref, allowMultiple: false),
                icon: const Icon(Icons.upload_file, size: 18),
                label: const Text('Upload'),
              ),
              const SizedBox(width: 12),
              ElevatedButton.icon(
                onPressed: () => _pickAndUpload(ref, allowMultiple: true),
                icon: const Icon(Icons.library_add, size: 18),
                label: const Text('Bulk upload'),
              ),
            ],
          ),
          const SizedBox(height: 4),
          const Text(
            'On a phone, "Upload" opens the camera or gallery — whichever the '
            'browser offers for an image file.',
            style: TextStyle(color: AppColors.textSecondary, fontSize: 12),
          ),
          const SizedBox(height: 16),
          Text('Try a sample', style: Theme.of(context).textTheme.titleSmall),
          const SizedBox(height: 8),
          samplesAsync.when(
            loading: () => const SizedBox(height: 36),
            error: (_, _) => const SizedBox(),
            data: (samples) => Wrap(
              spacing: 8,
              children: [
                for (final s in samples) _SampleChip(sample: s),
              ],
            ),
          ),
          const SizedBox(height: 16),
          Row(
            children: [
              const Text('Filter:'),
              const SizedBox(width: 8),
              DropdownButton<String?>(
                value: filter,
                items: const [
                  DropdownMenuItem(value: null, child: Text('All')),
                  DropdownMenuItem(value: 'needs_review', child: Text('Needs review')),
                  DropdownMenuItem(value: 'pending', child: Text('Pending')),
                  DropdownMenuItem(value: 'committed', child: Text('Committed')),
                  DropdownMenuItem(value: 'rejected', child: Text('Rejected')),
                ],
                onChanged: (v) => ref.read(documentStatusFilterProvider.notifier).state = v,
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _SampleChip extends ConsumerWidget {
  const _SampleChip({required this.sample});
  final SampleInfo sample;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return ActionChip(
      avatar: const Icon(Icons.auto_awesome, size: 16, color: AppColors.accent),
      label: Text(sample.label),
      onPressed: () async {
        final doc = await ref.read(documentsRepositoryProvider).trySample(sample.docType);
        ref.invalidate(documentsListProvider);
        ref.read(selectedDocumentIdProvider.notifier).state = doc.id;
      },
    );
  }
}

class _BulkUploadBanner extends ConsumerWidget {
  const _BulkUploadBanner();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final upload = ref.watch(bulkUploadProvider);
    if (upload.items.isEmpty) return const SizedBox();

    return Container(
      margin: const EdgeInsets.fromLTRB(24, 16, 24, 0),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: AppColors.slateMid,
        borderRadius: BorderRadius.circular(8),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Text(
                upload.inProgress
                    ? 'Uploading ${upload.items.length} files…'
                    : 'Commit ${upload.doneCount} high-confidence, review the rest '
                          '(${upload.errorCount} failed).',
              ),
              const Spacer(),
              if (!upload.inProgress)
                TextButton(
                  onPressed: () => ref.read(bulkUploadProvider.notifier).clear(),
                  child: const Text('Dismiss'),
                ),
            ],
          ),
          const SizedBox(height: 8),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: [
              for (final item in upload.items)
                Chip(
                  avatar: Icon(
                    switch (item.status) {
                      UploadItemStatus.uploading => Icons.hourglass_top,
                      UploadItemStatus.done => Icons.check_circle,
                      UploadItemStatus.error => Icons.error,
                    },
                    size: 16,
                    color: switch (item.status) {
                      UploadItemStatus.uploading => AppColors.textSecondary,
                      UploadItemStatus.done => AppColors.info,
                      UploadItemStatus.error => AppColors.critical,
                    },
                  ),
                  label: Text(item.filename, style: const TextStyle(fontSize: 12)),
                ),
            ],
          ),
        ],
      ),
    );
  }
}

class _DocumentList extends ConsumerWidget {
  const _DocumentList();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final documentsAsync = ref.watch(documentsListProvider);
    return documentsAsync.when(
      loading: () => const SkeletonList(),
      error: (err, _) => ErrorState(
        message: 'Could not load documents: $err',
        onRetry: () => ref.invalidate(documentsListProvider),
      ),
      data: (documents) {
        if (documents.isEmpty) {
          return const Center(
            child: Text('No documents here.', style: TextStyle(color: AppColors.textSecondary)),
          );
        }
        return ListView.separated(
          itemCount: documents.length,
          separatorBuilder: (_, _) => const Divider(height: 1),
          itemBuilder: (context, index) => _DocumentTile(doc: documents[index]),
        );
      },
    );
  }
}

class _DocumentTile extends ConsumerWidget {
  const _DocumentTile({required this.doc});
  final DocumentSummary doc;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final statusColor = switch (doc.status) {
      'needs_review' => AppColors.warning,
      'committed' => AppColors.info,
      'rejected' => AppColors.critical,
      _ => AppColors.textSecondary,
    };
    return ListTile(
      leading: Container(
        width: 10,
        height: 10,
        decoration: BoxDecoration(color: statusColor, shape: BoxShape.circle),
      ),
      title: Text(doc.type.replaceAll('_', ' ')),
      subtitle: Text(doc.status.replaceAll('_', ' ')),
      trailing: Text(
        doc.uploadedAt.split('T').first,
        style: const TextStyle(color: AppColors.textSecondary, fontSize: 12),
      ),
      onTap: () => ref.read(selectedDocumentIdProvider.notifier).state = doc.id,
    );
  }
}
