import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/theme.dart';
import '../../providers/timetable_providers.dart';

class ExplainPanel extends ConsumerWidget {
  const ExplainPanel({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final entryId = ref.watch(selectedEntryIdProvider);
    final explainAsync = ref.watch(explainProvider);

    return Container(
      width: 360,
      decoration: const BoxDecoration(
        color: AppColors.slateMid,
        border: Border(left: BorderSide(color: AppColors.slateLight)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Padding(
            padding: const EdgeInsets.all(16),
            child: Row(
              children: [
                Expanded(
                  child: Text('Explain', style: Theme.of(context).textTheme.titleMedium),
                ),
                IconButton(
                  icon: const Icon(Icons.close),
                  onPressed: () => ref.read(selectedEntryIdProvider.notifier).state = null,
                ),
              ],
            ),
          ),
          const Divider(height: 1),
          Expanded(
            child: entryId == null
                ? const Center(
                    child: Padding(
                      padding: EdgeInsets.all(24),
                      child: Text(
                        'Click any cell in the grid to see why it\'s scheduled there.',
                        style: TextStyle(color: AppColors.textSecondary),
                        textAlign: TextAlign.center,
                      ),
                    ),
                  )
                : explainAsync.when(
                    loading: () => const Padding(
                      padding: EdgeInsets.all(24),
                      child: Column(
                        children: [
                          CircularProgressIndicator(),
                          SizedBox(height: 16),
                          Text(
                            'Re-solving with this cell forbidden…',
                            style: TextStyle(color: AppColors.textSecondary),
                          ),
                        ],
                      ),
                    ),
                    error: (err, _) => Padding(
                      padding: const EdgeInsets.all(24),
                      child: Text('$err', style: const TextStyle(color: AppColors.critical)),
                    ),
                    data: (data) => data == null
                        ? const SizedBox()
                        : _ExplainBody(data: data),
                  ),
          ),
        ],
      ),
    );
  }
}

class _ExplainBody extends StatelessWidget {
  const _ExplainBody({required this.data});
  final Map<String, dynamic> data;

  @override
  Widget build(BuildContext context) {
    final reasons = (data['reasons'] as List).cast<String>();
    final alternatives = (data['alternatives'] as List).cast<Map<String, dynamic>>();
    final resolveDiff = data['resolve_diff'] as Map<String, dynamic>?;

    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        Text(
          data['title'] as String,
          style: Theme.of(context).textTheme.titleMedium?.copyWith(color: AppColors.accent),
        ),
        const SizedBox(height: 4),
        Text(
          '${data['class']} · ${data['slot']}',
          style: const TextStyle(color: AppColors.textSecondary),
        ),
        const SizedBox(height: 20),
        const Text('Why', style: TextStyle(fontWeight: FontWeight.bold)),
        const SizedBox(height: 8),
        for (final r in reasons) _Bullet(text: r),
        const SizedBox(height: 20),
        const Text('Ranked alternatives', style: TextStyle(fontWeight: FontWeight.bold)),
        const SizedBox(height: 8),
        if (alternatives.isEmpty)
          const Text('No feasible alternative slot found.', style: TextStyle(color: AppColors.textSecondary)),
        for (final alt in alternatives) _AlternativeCard(alt: alt),
        if (resolveDiff != null && resolveDiff['available'] == true) ...[
          const SizedBox(height: 20),
          const Text('If this cell were forbidden entirely', style: TextStyle(fontWeight: FontWeight.bold)),
          const SizedBox(height: 8),
          Text(
            'Re-solving the whole timetable without it changes the objective by '
            '${resolveDiff['objective_delta']}.',
            style: const TextStyle(color: AppColors.textSecondary),
          ),
        ],
      ],
    );
  }
}

class _Bullet extends StatelessWidget {
  const _Bullet({required this.text});
  final String text;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text('•  ', style: TextStyle(color: AppColors.accent)),
          Expanded(child: Text(text)),
        ],
      ),
    );
  }
}

class _AlternativeCard extends StatelessWidget {
  const _AlternativeCard({required this.alt});
  final Map<String, dynamic> alt;

  @override
  Widget build(BuildContext context) {
    final cost = (alt['cost_delta'] as num).toDouble();
    final sign = cost >= 0 ? '+' : '';
    final color = cost > 0 ? AppColors.warning : AppColors.info;
    return Card(
      margin: const EdgeInsets.only(bottom: 8),
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Row(
          children: [
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('${alt['slot']} · ${alt['room']}'),
                  ...((alt['reasons'] as List).cast<String>()).map(
                    (r) => Text(r, style: const TextStyle(fontSize: 12, color: AppColors.textSecondary)),
                  ),
                ],
              ),
            ),
            Text('$sign${cost.toInt()}', style: TextStyle(color: color, fontWeight: FontWeight.bold)),
          ],
        ),
      ),
    );
  }
}
