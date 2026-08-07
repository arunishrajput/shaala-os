import 'dart:convert';
import 'dart:typed_data';
import 'dart:ui' as ui;

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/skeleton.dart';
import '../../core/theme.dart';
import '../../data/models/document.dart';
import '../../data/repositories.dart';
import '../../providers/documents_providers.dart';

const _confidenceThreshold = 0.85;

class ReviewPanel extends ConsumerStatefulWidget {
  const ReviewPanel({this.fullWidth = false, super.key});

  /// True on narrow (phone-width) layouts, where this replaces the document
  /// list instead of sitting beside it — PROMPT.md §7.2's "responsive down
  /// to phone width" requirement, for a panel that's otherwise a fixed 680px.
  final bool fullWidth;

  @override
  ConsumerState<ReviewPanel> createState() => _ReviewPanelState();
}

class _ReviewPanelState extends ConsumerState<ReviewPanel> {
  final Map<int, TextEditingController> _controllers = {};
  final Map<int, String> _corrections = {};
  int? _activeFieldId;
  bool _committing = false;
  bool _rejecting = false;
  String? _commitError;

  @override
  void dispose() {
    for (final c in _controllers.values) {
      c.dispose();
    }
    super.dispose();
  }

  TextEditingController _controllerFor(ExtractedFieldModel field) {
    return _controllers.putIfAbsent(
      field.id,
      () => TextEditingController(text: field.value),
    );
  }

  Future<void> _commit(int documentId) async {
    setState(() {
      _committing = true;
      _commitError = null;
    });
    final corrections = [
      for (final entry in _corrections.entries)
        (fieldId: entry.key, correctedValue: entry.value),
    ];
    try {
      await ref
          .read(documentsRepositoryProvider)
          .commit(documentId, corrections);
      ref.invalidate(documentsListProvider);
      ref.read(selectedDocumentIdProvider.notifier).state = null;
    } catch (e) {
      setState(() => _commitError = friendlyError(e));
    } finally {
      if (mounted) setState(() => _committing = false);
    }
  }

  Future<void> _reject(int documentId) async {
    setState(() {
      _rejecting = true;
      _commitError = null;
    });
    try {
      await ref.read(documentsRepositoryProvider).reject(documentId);
      ref.invalidate(documentsListProvider);
      ref.read(selectedDocumentIdProvider.notifier).state = null;
    } catch (e) {
      setState(() => _commitError = friendlyError(e));
    } finally {
      if (mounted) setState(() => _rejecting = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final detailAsync = ref.watch(documentDetailProvider);

    return Container(
      width: widget.fullWidth ? null : 680,
      decoration: BoxDecoration(
        color: AppColors.slateMid,
        border: widget.fullWidth
            ? null
            : const Border(left: BorderSide(color: AppColors.slateLight)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Padding(
            padding: const EdgeInsets.all(16),
            child: Row(
              children: [
                Expanded(
                  child: Text(
                    'Review',
                    style: Theme.of(context).textTheme.titleMedium,
                  ),
                ),
                IconButton(
                  icon: const Icon(Icons.close),
                  onPressed: () =>
                      ref.read(selectedDocumentIdProvider.notifier).state =
                          null,
                ),
              ],
            ),
          ),
          const Divider(height: 1),
          Expanded(
            child: detailAsync.when(
              loading: () => const SkeletonList(count: 4),
              error: (err, _) => ErrorState(
                message: 'Could not load this document: ${friendlyError(err)}',
                onRetry: () => ref.invalidate(documentDetailProvider),
              ),
              data: (doc) {
                if (doc == null) return const SizedBox();
                final sorted = [...doc.fields]
                  ..sort((a, b) => a.confidence.compareTo(b.confidence));
                final activeBbox = sorted
                    .where((f) => f.id == _activeFieldId)
                    .map((f) => f.bbox)
                    .firstOrNull;

                return Column(
                  children: [
                    SizedBox(
                      height: 300,
                      child: _ImagePane(
                        dataUri: doc.originalUrl,
                        activeBbox: activeBbox,
                      ),
                    ),
                    if (doc.warnings.isNotEmpty)
                      _WarningsBanner(warnings: doc.warnings),
                    Expanded(
                      child: ListView(
                        padding: const EdgeInsets.all(16),
                        children: [
                          Text(
                            '${doc.type.replaceAll('_', ' ')} · doc-type confidence '
                            '${((doc.docTypeConfidence ?? 0) * 100).round()}%',
                            style: const TextStyle(
                              color: AppColors.textSecondary,
                            ),
                          ),
                          const SizedBox(height: 16),
                          for (final field in sorted)
                            _FieldEditor(
                              field: field,
                              controller: _controllerFor(field),
                              active: field.id == _activeFieldId,
                              onFocus: () =>
                                  setState(() => _activeFieldId = field.id),
                              onChanged: (v) => _corrections[field.id] = v,
                            ),
                          if (doc.rows.isNotEmpty) _RowsTable(rows: doc.rows),
                        ],
                      ),
                    ),
                    if (_commitError != null)
                      Padding(
                        padding: const EdgeInsets.symmetric(horizontal: 16),
                        child: Text(
                          _commitError!,
                          style: const TextStyle(color: AppColors.critical),
                        ),
                      ),
                    Padding(
                      padding: const EdgeInsets.all(16),
                      child: Row(
                        children: [
                          OutlinedButton(
                            onPressed: (_committing || _rejecting)
                                ? null
                                : () => _reject(doc.id),
                            child: Text(_rejecting ? 'Rejecting…' : 'Reject'),
                          ),
                          const Spacer(),
                          ElevatedButton(
                            onPressed: (_committing || _rejecting)
                                ? null
                                : () => _commit(doc.id),
                            child: Text(_committing ? 'Committing…' : 'Commit'),
                          ),
                        ],
                      ),
                    ),
                  ],
                );
              },
            ),
          ),
        ],
      ),
    );
  }
}

class _FieldEditor extends StatelessWidget {
  const _FieldEditor({
    required this.field,
    required this.controller,
    required this.active,
    required this.onFocus,
    required this.onChanged,
  });

  final ExtractedFieldModel field;
  final TextEditingController controller;
  final bool active;
  final VoidCallback onFocus;
  final ValueChanged<String> onChanged;

  @override
  Widget build(BuildContext context) {
    final lowConfidence = field.confidence < _confidenceThreshold;
    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: Focus(
        onFocusChange: (has) {
          if (has) onFocus();
        },
        child: TextField(
          controller: controller,
          onTap: onFocus,
          onChanged: onChanged,
          style: TextStyle(color: lowConfidence ? AppColors.warning : null),
          decoration: InputDecoration(
            labelText: field.name.replaceAll('_', ' '),
            helperText:
                '${(field.confidence * 100).round()}% confidence'
                '${lowConfidence ? ' — check this' : ''}',
            helperStyle: TextStyle(
              color: lowConfidence ? AppColors.warning : null,
            ),
            border: const OutlineInputBorder(),
            enabledBorder: OutlineInputBorder(
              borderSide: BorderSide(
                color: lowConfidence ? AppColors.warning : AppColors.slateLight,
                width: lowConfidence ? 2 : 1,
              ),
            ),
            focusedBorder: OutlineInputBorder(
              borderSide: BorderSide(
                color: active ? AppColors.accent : AppColors.slateLight,
                width: 2,
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class _RowsTable extends StatelessWidget {
  const _RowsTable({required this.rows});
  final List<Map<String, dynamic>> rows;

  @override
  Widget build(BuildContext context) {
    if (rows.isEmpty) return const SizedBox();
    final keys = rows.first.keys.toList();
    return Padding(
      padding: const EdgeInsets.only(top: 8),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            'Table rows (read-only in this phase)',
            style: TextStyle(color: AppColors.textSecondary, fontSize: 12),
          ),
          const SizedBox(height: 8),
          SingleChildScrollView(
            scrollDirection: Axis.horizontal,
            child: DataTable(
              columns: [for (final k in keys) DataColumn(label: Text(k))],
              rows: [
                for (final row in rows)
                  DataRow(
                    cells: [for (final k in keys) DataCell(Text('${row[k]}'))],
                  ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _WarningsBanner extends StatelessWidget {
  const _WarningsBanner({required this.warnings});
  final List<String> warnings;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      margin: const EdgeInsets.fromLTRB(16, 12, 16, 0),
      padding: const EdgeInsets.all(10),
      decoration: BoxDecoration(
        color: AppColors.warning.withValues(alpha: 0.15),
        borderRadius: BorderRadius.circular(8),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          for (final w in warnings)
            Text(w, style: const TextStyle(fontSize: 12)),
        ],
      ),
    );
  }
}

class _ImagePane extends StatefulWidget {
  const _ImagePane({required this.dataUri, required this.activeBbox});
  final String dataUri;
  final List<double>? activeBbox;

  @override
  State<_ImagePane> createState() => _ImagePaneState();
}

class _ImagePaneState extends State<_ImagePane> {
  Uint8List? _bytes;
  double? _aspectRatio;

  @override
  void initState() {
    super.initState();
    _decode();
  }

  @override
  void didUpdateWidget(covariant _ImagePane oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.dataUri != widget.dataUri) _decode();
  }

  Future<void> _decode() async {
    final bytes = base64Decode(widget.dataUri.split(',').last);
    final codec = await ui.instantiateImageCodec(bytes);
    final frame = await codec.getNextFrame();
    if (!mounted) return;
    setState(() {
      _bytes = bytes;
      _aspectRatio = frame.image.width / frame.image.height;
    });
  }

  @override
  Widget build(BuildContext context) {
    if (_bytes == null || _aspectRatio == null) {
      return const Center(child: CircularProgressIndicator());
    }
    return Container(
      color: Colors.black26,
      padding: const EdgeInsets.all(16),
      child: Center(
        child: AspectRatio(
          aspectRatio: _aspectRatio!,
          child: Stack(
            fit: StackFit.expand,
            children: [
              Image.memory(_bytes!, fit: BoxFit.fill),
              if (widget.activeBbox != null)
                Positioned.fill(
                  child: CustomPaint(painter: _BboxPainter(widget.activeBbox!)),
                ),
            ],
          ),
        ),
      ),
    );
  }
}

class _BboxPainter extends CustomPainter {
  const _BboxPainter(this.bbox);
  final List<double> bbox;

  @override
  void paint(Canvas canvas, Size size) {
    final rect = Rect.fromLTRB(
      bbox[0] * size.width,
      bbox[1] * size.height,
      bbox[2] * size.width,
      bbox[3] * size.height,
    ).inflate(4);
    final paint = Paint()
      ..color = AppColors.warning
      ..style = PaintingStyle.stroke
      ..strokeWidth = 3;
    canvas.drawRRect(
      RRect.fromRectAndRadius(rect, const Radius.circular(4)),
      paint,
    );
  }

  @override
  bool shouldRepaint(covariant _BboxPainter oldDelegate) =>
      oldDelegate.bbox != bbox;
}
