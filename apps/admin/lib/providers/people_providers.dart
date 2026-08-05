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

final classSectionsProvider = AsyncNotifierProvider<ClassSectionsNotifier, List<ClassSection>>(
  ClassSectionsNotifier.new,
);

final studentsByClassProvider = FutureProvider.family<List<Student>, int>((ref, classId) {
  return ref.read(peopleRepositoryProvider).fetchStudents(classId: classId);
});
