import 'package:fl_chart/fl_chart.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/skeleton.dart';
import '../../core/theme.dart';
import '../../data/models/staffing.dart';
import '../../data/repositories.dart';
import '../../providers/staffing_providers.dart';

class StaffingScreen extends ConsumerWidget {
  const StaffingScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final forecastAsync = ref.watch(staffingForecastProvider);
    final backtestAsync = ref.watch(staffingBacktestProvider);

    return SingleChildScrollView(
      padding: const EdgeInsets.all(24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'Staffing forecast',
            style: Theme.of(context).textTheme.headlineSmall,
          ),
          const SizedBox(height: 4),
          const Text(
            'Forecast, not prophecy — per-department EWMA + seasonal baseline over '
            'real absence history.',
            style: TextStyle(color: AppColors.textSecondary),
          ),
          const SizedBox(height: 20),
          forecastAsync.when(
            loading: () => const SkeletonList(count: 3),
            error: (err, _) => ErrorState(
              message: 'Could not load forecast: ${friendlyError(err)}',
              onRetry: () => ref.invalidate(staffingForecastProvider),
            ),
            data: (forecast) => _ForecastSection(forecast: forecast),
          ),
          const SizedBox(height: 32),
          Text(
            'Backtest — last 30 days',
            style: Theme.of(context).textTheme.titleMedium,
          ),
          const SizedBox(height: 12),
          backtestAsync.when(
            loading: () =>
                const SizedBox(height: 220, child: SkeletonList(count: 1)),
            error: (err, _) => ErrorState(
              message: 'Could not load backtest: ${friendlyError(err)}',
              onRetry: () => ref.invalidate(staffingBacktestProvider),
            ),
            data: (backtest) => _BacktestSection(backtest: backtest),
          ),
        ],
      ),
    );
  }
}

class _ForecastSection extends StatelessWidget {
  const _ForecastSection({required this.forecast});
  final StaffingForecast forecast;

  @override
  Widget build(BuildContext context) {
    final withRecommendation = forecast.departments
        .where((d) => d.recommendation != null)
        .toList();
    final quiet = forecast.departments
        .where((d) => d.recommendation == null)
        .toList();

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        if (withRecommendation.isEmpty)
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Row(
                children: [
                  const Icon(Icons.check_circle_outline, color: AppColors.info),
                  const SizedBox(width: 12),
                  const Text(
                    'No department shows elevated risk in the next 7 days.',
                  ),
                ],
              ),
            ),
          )
        else
          for (final d in withRecommendation) _DepartmentCard(department: d),
        if (quiet.isNotEmpty) ...[
          const SizedBox(height: 16),
          Text(
            'Other departments',
            style: TextStyle(color: AppColors.textSecondary, fontSize: 12),
          ),
          const SizedBox(height: 8),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: [
              for (final d in quiet)
                Chip(
                  label: Text('${d.department} · ${d.teacherCount} teachers'),
                  backgroundColor: AppColors.slateMid,
                ),
            ],
          ),
        ],
      ],
    );
  }
}

class _DepartmentCard extends StatelessWidget {
  const _DepartmentCard({required this.department});
  final DepartmentForecast department;

  @override
  Widget build(BuildContext context) {
    return Card(
      margin: const EdgeInsets.only(bottom: 12),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Row(
          children: [
            const Icon(Icons.insights_outlined, color: AppColors.warning),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    department.department,
                    style: const TextStyle(fontWeight: FontWeight.w600),
                  ),
                  const SizedBox(height: 2),
                  Text(
                    department.recommendation!,
                    style: const TextStyle(
                      color: AppColors.textSecondary,
                      fontSize: 13,
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _BacktestSection extends StatelessWidget {
  const _BacktestSection({required this.backtest});
  final StaffingBacktest backtest;

  @override
  Widget build(BuildContext context) {
    final byDate = <String, ({double predicted, double actual})>{};
    for (final p in backtest.points) {
      final existing = byDate[p.date] ?? (predicted: 0.0, actual: 0.0);
      byDate[p.date] = (
        predicted: existing.predicted + p.predicted,
        actual: existing.actual + p.actual,
      );
    }
    final dates = byDate.keys.toList()..sort();
    final predictedSpots = [
      for (var i = 0; i < dates.length; i++)
        FlSpot(i.toDouble(), byDate[dates[i]]!.predicted),
    ];
    final actualSpots = [
      for (var i = 0; i < dates.length; i++)
        FlSpot(i.toDouble(), byDate[dates[i]]!.actual),
    ];

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            _Legend(color: AppColors.accent, label: 'Predicted'),
            const SizedBox(width: 16),
            _Legend(color: AppColors.info, label: 'Actual'),
            const Spacer(),
            if (backtest.accuracyPct != null)
              Text(
                '${backtest.accuracyPct!.toStringAsFixed(1)}% better than a flat-average '
                'baseline · MAE ${backtest.mae?.toStringAsFixed(2)} teachers/day',
                style: const TextStyle(
                  color: AppColors.textSecondary,
                  fontSize: 12,
                ),
              ),
          ],
        ),
        const SizedBox(height: 12),
        SizedBox(
          height: 220,
          child: dates.isEmpty
              ? const Center(
                  child: Text(
                    'Not enough history yet.',
                    style: TextStyle(color: AppColors.textSecondary),
                  ),
                )
              : LineChart(
                  LineChartData(
                    gridData: const FlGridData(
                      show: true,
                      drawVerticalLine: false,
                    ),
                    titlesData: const FlTitlesData(
                      topTitles: AxisTitles(
                        sideTitles: SideTitles(showTitles: false),
                      ),
                      rightTitles: AxisTitles(
                        sideTitles: SideTitles(showTitles: false),
                      ),
                      bottomTitles: AxisTitles(
                        sideTitles: SideTitles(showTitles: false),
                      ),
                    ),
                    borderData: FlBorderData(show: false),
                    lineBarsData: [
                      LineChartBarData(
                        spots: predictedSpots,
                        color: AppColors.accent,
                        barWidth: 2,
                        dotData: const FlDotData(show: false),
                      ),
                      LineChartBarData(
                        spots: actualSpots,
                        color: AppColors.info,
                        barWidth: 2,
                        dotData: const FlDotData(show: false),
                      ),
                    ],
                  ),
                ),
        ),
      ],
    );
  }
}

class _Legend extends StatelessWidget {
  const _Legend({required this.color, required this.label});
  final Color color;
  final String label;

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Container(
          width: 10,
          height: 10,
          decoration: BoxDecoration(color: color, shape: BoxShape.circle),
        ),
        const SizedBox(width: 6),
        Text(label, style: const TextStyle(fontSize: 12)),
      ],
    );
  }
}
