import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:web/web.dart' as web;

import '../../core/theme.dart';
import '../../data/repositories.dart';
import '../../providers/actions_providers.dart';
import '../../providers/core_providers.dart';

class _NavDestination {
  const _NavDestination(this.path, this.label, this.icon);
  final String path;
  final String label;
  final IconData icon;
}

const _destinations = [
  _NavDestination('/dashboard', 'Dashboard', Icons.dashboard_outlined),
  _NavDestination('/timetable', 'Timetable', Icons.calendar_view_week_outlined),
  _NavDestination('/documents', 'Documents', Icons.document_scanner_outlined),
  _NavDestination('/attendance', 'Attendance', Icons.qr_code_scanner_outlined),
  _NavDestination('/people', 'People', Icons.people_outline),
  _NavDestination('/staffing', 'Staffing', Icons.insights_outlined),
];

class AppShell extends ConsumerWidget {
  const AppShell({required this.child, super.key});
  final Widget child;

  int _indexFor(BuildContext context) {
    final location = GoRouterState.of(context).uri.path;
    final index = _destinations.indexWhere((d) => location.startsWith(d.path));
    return index < 0 ? 0 : index;
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final selectedIndex = _indexFor(context);
    final wide = MediaQuery.sizeOf(context).width >= 700;

    void onSelect(int index) => context.go(_destinations[index].path);

    return Scaffold(
      appBar: AppBar(
        title: Row(
          children: [
            const Text('Shaala OS'),
            const SizedBox(width: 16),
            Text(
              'Shaala Public School',
              style: TextStyle(color: AppColors.textSecondary, fontSize: 14),
            ),
            const Spacer(),
            const _LiveClock(),
            const SizedBox(width: 16),
            const _WsBadge(),
            const SizedBox(width: 16),
            const _ResetDemoButton(),
            const SizedBox(width: 8),
            const _ActionBell(),
          ],
        ),
      ),
      body: wide
          ? Row(
              children: [
                NavigationRail(
                  selectedIndex: selectedIndex,
                  onDestinationSelected: onSelect,
                  extended: MediaQuery.sizeOf(context).width >= 1000,
                  labelType: NavigationRailLabelType.none,
                  destinations: [
                    for (final d in _destinations)
                      NavigationRailDestination(
                        icon: Icon(d.icon),
                        label: Text(d.label),
                      ),
                  ],
                ),
                const VerticalDivider(width: 1),
                Expanded(child: child),
              ],
            )
          : child,
      bottomNavigationBar: wide
          ? null
          : NavigationBar(
              selectedIndex: selectedIndex,
              onDestinationSelected: onSelect,
              destinations: [
                for (final d in _destinations)
                  NavigationDestination(icon: Icon(d.icon), label: d.label),
              ],
            ),
    );
  }
}

class _LiveClock extends StatefulWidget {
  const _LiveClock();

  @override
  State<_LiveClock> createState() => _LiveClockState();
}

class _LiveClockState extends State<_LiveClock> {
  late Timer _timer;
  DateTime _now = DateTime.now();

  @override
  void initState() {
    super.initState();
    _timer = Timer.periodic(const Duration(seconds: 1), (_) {
      setState(() => _now = DateTime.now());
    });
  }

  @override
  void dispose() {
    _timer.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final h = _now.hour.toString().padLeft(2, '0');
    final m = _now.minute.toString().padLeft(2, '0');
    final s = _now.second.toString().padLeft(2, '0');
    return Text(
      '$h:$m:$s',
      style: const TextStyle(color: AppColors.textSecondary),
    );
  }
}

class _ActionBell extends ConsumerWidget {
  const _ActionBell();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final count = ref.watch(openActionsCountProvider);
    return IconButton(
      tooltip: count == 0
          ? 'Action Center'
          : '$count item${count == 1 ? '' : 's'} need attention',
      onPressed: () => context.go('/dashboard'),
      icon: Badge(
        label: Text('$count'),
        isLabelVisible: count > 0,
        backgroundColor: AppColors.critical,
        child: const Icon(Icons.notifications_none),
      ),
    );
  }
}

class _ResetDemoButton extends ConsumerWidget {
  const _ResetDemoButton();

  Future<void> _confirmAndReset(BuildContext context, WidgetRef ref) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (dialogContext) => AlertDialog(
        title: const Text('Reset demo data?'),
        content: const Text(
          'Restores the fixed seed dataset — every student, teacher, timetable, '
          'document, and attendance record. Anything changed this session is lost.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(dialogContext).pop(false),
            child: const Text('Cancel'),
          ),
          FilledButton(
            onPressed: () => Navigator.of(dialogContext).pop(true),
            child: const Text('Reset'),
          ),
        ],
      ),
    );
    if (confirmed != true || !context.mounted) return;

    unawaited(
      showDialog<void>(
        context: context,
        barrierDismissible: false,
        builder: (_) => const AlertDialog(
          content: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              SizedBox(
                width: 20,
                height: 20,
                child: CircularProgressIndicator(strokeWidth: 2),
              ),
              SizedBox(width: 16),
              Text('Resetting demo data…'),
            ],
          ),
        ),
      ),
    );

    try {
      await ref.read(demoRepositoryProvider).reset();
      // Every id in every provider is now potentially stale (new seed run =
      // new primary keys) -- a full reload is the only way to guarantee
      // nothing in the UI still points at data that no longer exists.
      web.window.location.reload();
    } catch (e) {
      if (!context.mounted) return;
      Navigator.of(context).pop();
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Reset failed: ${friendlyError(e)}')),
      );
    }
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return IconButton(
      tooltip: 'Reset demo data',
      onPressed: () => _confirmAndReset(context, ref),
      icon: const Icon(Icons.restart_alt),
    );
  }
}

class _WsBadge extends ConsumerWidget {
  const _WsBadge();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final events = ref.watch(eventStreamProvider);
    final connected = events.hasValue;
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Container(
          width: 10,
          height: 10,
          decoration: BoxDecoration(
            shape: BoxShape.circle,
            color: connected ? AppColors.info : AppColors.textSecondary,
          ),
        ),
        const SizedBox(width: 6),
        Text(
          connected ? 'Live' : 'Connecting…',
          style: const TextStyle(color: AppColors.textSecondary, fontSize: 12),
        ),
      ],
    );
  }
}
