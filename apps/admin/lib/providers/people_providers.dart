import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../data/models/class_section.dart';
import '../data/models/student.dart';
import '../data/models/teacher.dart';
import 'core_providers.dart';

class TeachersNotifier extends AsyncNotifier<List<Teacher>> {
  @override
  Future<List<Teacher>> build() {
    return ref.read(peopleRepositoryProvider).fetchTeachers();
  }
}

final teachersProvider = AsyncNotifierProvider<TeachersNotifier, List<Teacher>>(
  TeachersNotifier.new,
);

class ClassSectionsNotifier extends AsyncNotifier<List<ClassSection>> {
  @override
  Future<List<ClassSection>> build() {
    return ref.read(peopleRepositoryProvider).fetchClasses();
  }
}

final classSectionsProvider =
    AsyncNotifierProvider<ClassSectionsNotifier, List<ClassSection>>(
      ClassSectionsNotifier.new,
    );

final studentsByClassProvider = FutureProvider.family<List<Student>, int>((
  ref,
  classId,
) {
  return ref.read(peopleRepositoryProvider).fetchStudents(classId: classId);
});

/// The WebSocket is the single source of truth for "something changed"
/// (PROMPT.md §7.3) — this self-invalidates on document.committed so the
/// dashboard's student count reacts live when an admission form is committed,
/// without the dashboard screen needing to know why.
class StudentsCountNotifier extends AsyncNotifier<int> {
  @override
  Future<int> build() {
    ref.listen(eventStreamProvider, (_, next) {
      if (next.value?.type == 'document.committed') ref.invalidateSelf();
    });
    return ref
        .read(peopleRepositoryProvider)
        .fetchStudents()
        .then((s) => s.length);
  }
}

final studentsCountProvider = AsyncNotifierProvider<StudentsCountNotifier, int>(
  StudentsCountNotifier.new,
);
