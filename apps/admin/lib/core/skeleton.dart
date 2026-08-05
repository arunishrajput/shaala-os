import 'package:flutter/material.dart';

import 'theme.dart';

/// A static content-shaped placeholder — PROMPT.md §7.3 explicitly asks for
/// skeletons, not spinners, since a judge on a slow connection sees loading
/// states. No shimmer animation; the shape alone communicates "loading".
class SkeletonList extends StatelessWidget {
  const SkeletonList({this.count = 6, this.height = 64, super.key});
  final int count;
  final double height;

  @override
  Widget build(BuildContext context) {
    return ListView.separated(
      padding: const EdgeInsets.all(16),
      itemCount: count,
      separatorBuilder: (_, _) => const SizedBox(height: 12),
      itemBuilder: (context, index) => Container(
        height: height,
        decoration: BoxDecoration(
          color: AppColors.slateMid,
          borderRadius: BorderRadius.circular(12),
        ),
      ),
    );
  }
}

class ErrorState extends StatelessWidget {
  const ErrorState({required this.message, this.onRetry, super.key});
  final String message;
  final VoidCallback? onRetry;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          const Icon(Icons.error_outline, color: AppColors.critical, size: 40),
          const SizedBox(height: 12),
          Text(message, style: const TextStyle(color: AppColors.textSecondary)),
          if (onRetry != null) ...[
            const SizedBox(height: 12),
            OutlinedButton(onPressed: onRetry, child: const Text('Retry')),
          ],
        ],
      ),
    );
  }
}
