import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/theme.dart';
import '../../providers/core_providers.dart';

// ─── Role definitions ────────────────────────────────────────────────────────

class _RoleDef {
  const _RoleDef({
    required this.role,
    required this.label,
    required this.description,
    required this.icon,
    required this.iconColor,
    required this.iconBg,
  });
  final String role;
  final String label;
  final String description;
  final IconData icon;
  final Color iconColor;
  final Color iconBg;
}

const _roles = [
  _RoleDef(
    role: 'admin',
    label: 'Administrator',
    description: 'Manage school operations & staff',
    icon: Icons.admin_panel_settings_rounded,
    iconColor: AppColors.accent,
    iconBg: Color(0xFFEEF2FF),
  ),
  _RoleDef(
    role: 'teacher',
    label: 'Teacher',
    description: 'Manage classes & student progress',
    icon: Icons.people_rounded,
    iconColor: Color(0xFF059669),
    iconBg: Color(0xFFECFDF5),
  ),
  _RoleDef(
    role: 'parent',
    label: 'Parent',
    description: 'Stay updated on your child',
    icon: Icons.person_rounded,
    iconColor: Color(0xFF0284C7),
    iconBg: Color(0xFFEFF6FF),
  ),
];

// ─── Screen ──────────────────────────────────────────────────────────────────

class LoginScreen extends ConsumerWidget {
  const LoginScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final auth = ref.watch(authProvider);

    return Scaffold(
      backgroundColor: Colors.white,
      body: SafeArea(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Expanded(
              child: SingleChildScrollView(
                padding:
                    const EdgeInsets.symmetric(horizontal: 20, vertical: 24),
                child: _FadeInUp(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const SizedBox(height: 8),

                      // ── Logo ──────────────────────────────────────────────
                      Container(
                        width: 52,
                        height: 52,
                        decoration: BoxDecoration(
                          color: const Color(0xFFEEF2FF),
                          borderRadius: BorderRadius.circular(14),
                        ),
                        child: const Icon(
                          Icons.school_rounded,
                          color: AppColors.accent,
                          size: 30,
                        ),
                      ),
                      const SizedBox(height: 28),

                      // ── Heading ───────────────────────────────────────────
                      RichText(
                        text: TextSpan(
                          style: Theme.of(context)
                              .textTheme
                              .headlineMedium
                              ?.copyWith(
                                height: 1.25,
                                color: AppColors.textPrimary,
                              ),
                          children: const [
                            TextSpan(
                              text: 'Welcome to\n',
                              style: TextStyle(fontWeight: FontWeight.w400),
                            ),
                            TextSpan(
                              text: 'Shaala OS',
                              style: TextStyle(fontWeight: FontWeight.w700),
                            ),
                          ],
                        ),
                      ),
                      const SizedBox(height: 8),
                      Text(
                        'Choose your role to continue',
                        style: Theme.of(context).textTheme.bodyLarge?.copyWith(
                              color: AppColors.textSecondary,
                            ),
                      ),
                      const SizedBox(height: 36),

                      // ── Error banner ──────────────────────────────────────
                      if (auth.error != null) ...[
                        Container(
                          width: double.infinity,
                          padding: const EdgeInsets.all(12),
                          decoration: BoxDecoration(
                            color: AppColors.critical.withValues(alpha: 0.08),
                            borderRadius: BorderRadius.circular(10),
                          ),
                          child: Text(
                            auth.error!,
                            style: const TextStyle(
                              color: AppColors.critical,
                              fontSize: 14,
                            ),
                          ),
                        ),
                        const SizedBox(height: 16),
                      ],

                      // ── Role cards ────────────────────────────────────────
                      for (int i = 0; i < _roles.length; i++) ...[
                        if (i > 0) const SizedBox(height: 12),
                        _RoleCard(def: _roles[i]),
                      ],
                    ],
                  ),
                ),
              ),
            ),

            // ── Footer ────────────────────────────────────────────────────
            const Padding(
              padding: EdgeInsets.only(bottom: 20, top: 8),
              child: Center(
                child: Text(
                  'Secure demo login',
                  style: TextStyle(
                    color: AppColors.textSecondary,
                    fontSize: 12,
                    letterSpacing: 0.2,
                  ),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

// ─── Role card ────────────────────────────────────────────────────────────────

class _RoleCard extends ConsumerWidget {
  const _RoleCard({required this.def});
  final _RoleDef def;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final auth = ref.watch(authProvider);
    final loading = auth.loadingRole == def.role;
    final anyLoading = auth.loading;

    return Material(
      color: Colors.white,
      borderRadius: BorderRadius.circular(16),
      child: InkWell(
        borderRadius: BorderRadius.circular(16),
        onTap: anyLoading
            ? null
            : () => ref.read(authProvider.notifier).demoLogin(def.role),
        child: Container(
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(16),
            border: Border.all(
              color: const Color(0xFFE2E8F0),
              width: 1,
            ),
          ),
          padding:
              const EdgeInsets.symmetric(horizontal: 16, vertical: 16),
          child: Row(
            children: [
              // ── Icon container ──────────────────────────────────────────
              Container(
                width: 46,
                height: 46,
                decoration: BoxDecoration(
                  color: def.iconBg,
                  borderRadius: BorderRadius.circular(12),
                ),
                child: loading
                    ? Center(
                        child: SizedBox(
                          width: 20,
                          height: 20,
                          child: CircularProgressIndicator(
                            strokeWidth: 2,
                            color: def.iconColor,
                          ),
                        ),
                      )
                    : Icon(def.icon, color: def.iconColor, size: 24),
              ),
              const SizedBox(width: 16),

              // ── Label + description ────────────────────────────────────
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      def.label,
                      style: const TextStyle(
                        fontSize: 16,
                        fontWeight: FontWeight.w600,
                        color: AppColors.textPrimary,
                        height: 1.2,
                      ),
                    ),
                    const SizedBox(height: 3),
                    Text(
                      def.description,
                      style: const TextStyle(
                        fontSize: 13,
                        color: AppColors.textSecondary,
                        height: 1.3,
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(width: 8),

              // ── Chevron ────────────────────────────────────────────────
              Icon(
                Icons.chevron_right_rounded,
                color: anyLoading && !loading
                    ? const Color(0xFFE2E8F0)
                    : const Color(0xFF94A3B8),
                size: 22,
              ),
            ],
          ),
        ),
      ),
    );
  }
}

// ─── Entrance animation ───────────────────────────────────────────────────────

/// A single restrained entrance: fade + short rise. Kept from the original
/// design — one orchestrated moment reads as intentional on a quiet screen.
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
        child: Transform.translate(
          offset: Offset(0, (1 - t) * 16),
          child: child,
        ),
      ),
      child: child,
    );
  }
}
