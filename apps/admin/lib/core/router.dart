import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../features/attendance/attendance_screen.dart';
import '../features/auth/login_screen.dart';
import '../features/dashboard/app_shell.dart';
import '../features/dashboard/dashboard_screen.dart';
import '../features/documents/documents_screen.dart';
import '../features/people/class_students_screen.dart';
import '../features/people/people_screen.dart';
import '../features/staffing/staffing_screen.dart';
import '../features/timetable/timetable_screen.dart';

import '../providers/core_providers.dart';

class _RouterRefreshNotifier extends ChangeNotifier {
  _RouterRefreshNotifier(Ref ref) {
    ref.listen(authProvider, (_, _) => notifyListeners());
  }
}

final routerProvider = Provider<GoRouter>((ref) {
  final refresh = _RouterRefreshNotifier(ref);

  return GoRouter(
    initialLocation: '/login',
    refreshListenable: refresh,
    redirect: (context, state) {
      final loggedIn = ref.read(authProvider).isLoggedIn;
      final loggingIn = state.matchedLocation == '/login';
      if (!loggedIn && !loggingIn) return '/login';
      if (loggedIn && loggingIn) return '/dashboard';
      return null;
    },
    routes: [
      GoRoute(path: '/login', builder: (context, state) => const LoginScreen()),
      ShellRoute(
        builder: (context, state, child) => AppShell(child: child),
        routes: [
          GoRoute(path: '/dashboard', builder: (context, state) => const DashboardScreen()),
          GoRoute(path: '/timetable', builder: (context, state) => const TimetableScreen()),
          GoRoute(path: '/documents', builder: (context, state) => const DocumentsScreen()),
          GoRoute(
            path: '/attendance',
            builder: (context, state) => const AttendanceScreen(),
          ),
          GoRoute(
            path: '/people',
            builder: (context, state) => const PeopleScreen(),
            routes: [
              GoRoute(
                path: 'class/:id',
                builder: (context, state) => ClassStudentsScreen(
                  classId: int.parse(state.pathParameters['id']!),
                  classLabel: state.extra as String?,
                ),
              ),
            ],
          ),
          GoRoute(path: '/staffing', builder: (context, state) => const StaffingScreen()),
        ],
      ),
    ],
  );
});
