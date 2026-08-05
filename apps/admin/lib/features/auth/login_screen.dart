import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/theme.dart';
import '../../providers/core_providers.dart';

class LoginScreen extends ConsumerWidget {
  const LoginScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final auth = ref.watch(authProvider);

    return Scaffold(
      body: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 420),
          child: Padding(
            padding: const EdgeInsets.all(32),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                Text(
                  'Shaala OS',
                  textAlign: TextAlign.center,
                  style: Theme.of(context).textTheme.headlineMedium?.copyWith(
                    fontWeight: FontWeight.bold,
                    color: AppColors.accent,
                  ),
                ),
                const SizedBox(height: 8),
                Text(
                  'Paper in, decisions out.',
                  textAlign: TextAlign.center,
                  style: Theme.of(
                    context,
                  ).textTheme.bodyLarge?.copyWith(color: AppColors.textSecondary),
                ),
                const SizedBox(height: 40),
                if (auth.error != null) ...[
                  Text(
                    auth.error!,
                    textAlign: TextAlign.center,
                    style: const TextStyle(color: AppColors.critical),
                  ),
                  const SizedBox(height: 16),
                ],
                _DemoLoginButton(role: 'admin', label: 'Continue as Admin'),
                const SizedBox(height: 12),
                _DemoLoginButton(role: 'teacher', label: 'Continue as Teacher'),
                const SizedBox(height: 12),
                _DemoLoginButton(role: 'parent', label: 'Continue as Parent'),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _DemoLoginButton extends ConsumerWidget {
  const _DemoLoginButton({required this.role, required this.label});

  final String role;
  final String label;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final loading = ref.watch(authProvider).loading;
    return ElevatedButton(
      onPressed: loading ? null : () => ref.read(authProvider.notifier).demoLogin(role),
      child: Text(label),
    );
  }
}
