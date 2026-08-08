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
      body: Stack(
        children: [
          const Positioned.fill(child: _RuledPaperBackground()),
          Center(
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 420),
              child: Padding(
                padding: const EdgeInsets.all(32),
                child: _FadeInUp(
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      Text(
                        'Shaala OS',
                        textAlign: TextAlign.center,
                        style: Theme.of(context).textTheme.headlineMedium
                            ?.copyWith(color: AppColors.accent, height: 1.1),
                      ),
                      const SizedBox(height: 8),
                      Text(
                        'Paper in, decisions out.',
                        textAlign: TextAlign.center,
                        style: Theme.of(
                          context,
                        ).textTheme.bodyLarge?.copyWith(
                          color: AppColors.textSecondary,
                          letterSpacing: 0.2,
                        ),
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
                      _DemoLoginButton(
                        role: 'admin',
                        label: 'Continue as Admin',
                        primary: true,
                      ),
                      const SizedBox(height: 12),
                      _DemoLoginButton(
                        role: 'teacher',
                        label: 'Continue as Teacher',
                      ),
                      const SizedBox(height: 12),
                      _DemoLoginButton(
                        role: 'parent',
                        label: 'Continue as Parent',
                      ),
                    ],
                  ),
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

/// A single restrained entrance: fade + a short rise. One orchestrated
/// moment reads as intentional; several scattered animated bits would read
/// as noise on a screen this quiet.
class _FadeInUp extends StatelessWidget {
  const _FadeInUp({required this.child});
  final Widget child;

  @override
  Widget build(BuildContext context) {
    return TweenAnimationBuilder<double>(
      tween: Tween(begin: 0, end: 1),
      duration: const Duration(milliseconds: 500),
      curve: Curves.easeOutCubic,
      builder: (context, t, child) => Opacity(
        opacity: t,
        child: Transform.translate(offset: Offset(0, (1 - t) * 16), child: child),
      ),
      child: child,
    );
  }
}

/// A faint register-paper texture -- horizontal rules plus a single margin
/// line, the specific material this product's whole thesis is about
/// digitizing. Deliberately quiet: this is texture, not a pattern anyone
/// should consciously notice.
class _RuledPaperBackground extends StatelessWidget {
  const _RuledPaperBackground();

  @override
  Widget build(BuildContext context) {
    return CustomPaint(painter: _RuledPaperPainter());
  }
}

class _RuledPaperPainter extends CustomPainter {
  static const _lineSpacing = 40.0;
  static const _marginInset = 72.0;

  @override
  void paint(Canvas canvas, Size size) {
    final rulePaint = Paint()
      ..color = AppColors.slateLight.withValues(alpha: 0.55)
      ..strokeWidth = 1;
    for (var y = _lineSpacing; y < size.height; y += _lineSpacing) {
      canvas.drawLine(Offset(0, y), Offset(size.width, y), rulePaint);
    }

    if (size.width > _marginInset + 40) {
      final marginPaint = Paint()
        ..color = AppColors.accent.withValues(alpha: 0.22)
        ..strokeWidth = 1;
      canvas.drawLine(
        Offset(_marginInset, 0),
        Offset(_marginInset, size.height),
        marginPaint,
      );
    }
  }

  @override
  bool shouldRepaint(covariant _RuledPaperPainter oldDelegate) => false;
}

class _DemoLoginButton extends ConsumerWidget {
  const _DemoLoginButton({
    required this.role,
    required this.label,
    this.primary = false,
  });

  final String role;
  final String label;
  final bool primary;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final auth = ref.watch(authProvider);
    final thisButtonLoading = auth.loadingRole == role;
    final onPressed = auth.loading
        ? null
        : () => ref.read(authProvider.notifier).demoLogin(role);
    final child = thisButtonLoading
        ? const SizedBox(
            width: 18,
            height: 18,
            child: CircularProgressIndicator(strokeWidth: 2),
          )
        : Text(label);

    if (primary) {
      return ElevatedButton(onPressed: onPressed, child: child);
    }
    return OutlinedButton(
      onPressed: onPressed,
      style: OutlinedButton.styleFrom(
        foregroundColor: AppColors.textPrimary,
        side: const BorderSide(color: AppColors.slateLight),
        padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 14),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      ),
      child: child,
    );
  }
}
