import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/skeleton.dart';
import '../../core/theme.dart';
import '../../data/models/class_section.dart';
import '../../data/models/teacher.dart';
import '../../providers/people_providers.dart';

class PeopleScreen extends StatefulWidget {
  const PeopleScreen({super.key});

  @override
  State<PeopleScreen> createState() => _PeopleScreenState();
}

class _PeopleScreenState extends State<PeopleScreen> with SingleTickerProviderStateMixin {
  late final TabController _tabController = TabController(length: 2, vsync: this);

  @override
  void dispose() {
    _tabController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
          child: TabBar(
            controller: _tabController,
            isScrollable: true,
            labelColor: AppColors.accent,
            unselectedLabelColor: AppColors.textSecondary,
            indicatorColor: AppColors.accent,
            tabs: const [Tab(text: 'Teachers'), Tab(text: 'Classes')],
          ),
        ),
        Expanded(
          child: TabBarView(
            controller: _tabController,
            children: const [_TeachersTab(), _ClassesTab()],
          ),
        ),
      ],
    );
  }
}

class _TeachersTab extends ConsumerWidget {
  const _TeachersTab();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final teachers = ref.watch(teachersProvider);
    return teachers.when(
      loading: () => const SkeletonList(),
      error: (err, _) => ErrorState(
        message: 'Could not load teachers: $err',
        onRetry: () => ref.invalidate(teachersProvider),
      ),
      data: (list) => ListView.separated(
        padding: const EdgeInsets.all(16),
        itemCount: list.length,
        separatorBuilder: (_, _) => const Divider(height: 1),
        itemBuilder: (context, index) => _TeacherTile(teacher: list[index]),
      ),
    );
  }
}

class _TeacherTile extends StatelessWidget {
  const _TeacherTile({required this.teacher});
  final Teacher teacher;

  @override
  Widget build(BuildContext context) {
    return ListTile(
      leading: CircleAvatar(
        backgroundColor: AppColors.accent.withValues(alpha: 0.2),
        child: Text(
          teacher.name.isNotEmpty ? teacher.name[0] : '?',
          style: const TextStyle(color: AppColors.accent),
        ),
      ),
      title: Text(teacher.name),
      subtitle: Text('${teacher.dept} · ${teacher.code} · ${teacher.phone}'),
      trailing: Text(
        '${teacher.maxPeriodsPerWeek} periods/wk',
        style: const TextStyle(color: AppColors.textSecondary, fontSize: 12),
      ),
    );
  }
}

class _ClassesTab extends ConsumerWidget {
  const _ClassesTab();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final classes = ref.watch(classSectionsProvider);
    return classes.when(
      loading: () => const SkeletonList(),
      error: (err, _) => ErrorState(
        message: 'Could not load classes: $err',
        onRetry: () => ref.invalidate(classSectionsProvider),
      ),
      data: (list) => ListView.separated(
        padding: const EdgeInsets.all(16),
        itemCount: list.length,
        separatorBuilder: (_, _) => const Divider(height: 1),
        itemBuilder: (context, index) {
          final cs = list[index];
          return _ClassTile(classSection: cs);
        },
      ),
    );
  }
}

class _ClassTile extends StatelessWidget {
  const _ClassTile({required this.classSection});
  final ClassSection classSection;

  @override
  Widget build(BuildContext context) {
    return ListTile(
      leading: const Icon(Icons.groups_outlined, color: AppColors.textSecondary),
      title: Text(classSection.label),
      subtitle: Text('${classSection.strength} students'),
      trailing: const Icon(Icons.chevron_right, color: AppColors.textSecondary),
      onTap: () => context.go('/people/class/${classSection.id}', extra: classSection.label),
    );
  }
}
