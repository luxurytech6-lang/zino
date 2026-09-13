"""
Predictive CGPA engine.

Methodology
-----------
1. Weighted Average (ground truth so far):
   Semester GPA   = sum(grade_point * credit_units) / sum(credit_units)
   CGPA            = same formula applied cumulatively across ALL semesters recorded

2. Linear Projection (trend forecast):
   Treat each semester's GPA as a point (x = semester index, y = GPA) and fit
   a least-squares regression line y = mx + b. Project forward to estimate
   the GPA trend for the next semester(s).

3. Recency-Weighted Blend (stabilizer):
   A pure linear projection can overreact to a single unusual semester.
   We blend the raw linear projection with a recency-weighted average of the
   last up-to-3 semesters (most recent semester weighted highest) to produce
   a more stable "predicted next semester GPA". The predicted CGPA is then
   the cumulative CGPA recomputed as if that predicted semester happened.
"""


def linear_regression(xs, ys):
    """Simple least-squares fit. Returns (slope, intercept)."""
    n = len(xs)
    if n == 0:
        return 0.0, 0.0
    if n == 1:
        return 0.0, ys[0]

    mean_x = sum(xs) / n
    mean_y = sum(ys) / n
    numerator = sum((xs[i] - mean_x) * (ys[i] - mean_y) for i in range(n))
    denominator = sum((xs[i] - mean_x) ** 2 for i in range(n))

    if denominator == 0:
        return 0.0, mean_y

    slope = numerator / denominator
    intercept = mean_y - slope * mean_x
    return slope, intercept


def recency_weighted_average(values, max_terms=3):
    """Weighted average of the last `max_terms` values, most recent = highest weight."""
    recent = values[-max_terms:]
    n = len(recent)
    if n == 0:
        return 0.0
    weights = list(range(1, n + 1))  # e.g. [1,2,3] -> last item weighted 3x
    weighted_sum = sum(v * w for v, w in zip(recent, weights))
    return weighted_sum / sum(weights)


def clamp(value, low=0.0, high=5.0):
    return max(low, min(high, value))


def predict_next_gpa(semester_gpas):
    """
    semester_gpas: list of floats, chronological order.
    Returns dict with linear projection, recency-weighted average, and blended prediction.
    """
    if not semester_gpas:
        return {
            "has_prediction": False,
            "linear_projection": None,
            "recency_weighted": None,
            "blended_prediction": None,
        }

    if len(semester_gpas) == 1:
        # Not enough points for a trend line; fall back to the only data point
        only = semester_gpas[0]
        return {
            "has_prediction": True,
            "linear_projection": round(only, 2),
            "recency_weighted": round(only, 2),
            "blended_prediction": round(only, 2),
        }

    xs = list(range(1, len(semester_gpas) + 1))
    slope, intercept = linear_regression(xs, semester_gpas)
    next_x = len(semester_gpas) + 1
    linear_proj = clamp(slope * next_x + intercept)

    recency_avg = clamp(recency_weighted_average(semester_gpas))

    # Blend: 55% recency-weighted average (stability) + 45% linear trend (direction)
    blended = clamp(0.55 * recency_avg + 0.45 * linear_proj)

    return {
        "has_prediction": True,
        "linear_projection": round(linear_proj, 2),
        "recency_weighted": round(recency_avg, 2),
        "blended_prediction": round(blended, 2),
        "trend_slope": round(slope, 3),
    }


def predict_future_cgpa(semester_history, predicted_next_gpa, avg_units_per_semester, future_semesters=1):
    """
    semester_history: list of dicts [{'gpa': float, 'units': int}, ...] chronological
    predicted_next_gpa: blended predicted GPA for the upcoming semester
    avg_units_per_semester: average credit load, used to weight the predicted semester
    future_semesters: how many semesters ahead to project (repeats the predicted GPA trend)

    Returns projected cumulative CGPA after `future_semesters` more semesters.
    """
    total_points = sum(s["gpa"] * s["units"] for s in semester_history)
    total_units = sum(s["units"] for s in semester_history)

    for _ in range(future_semesters):
        total_points += predicted_next_gpa * avg_units_per_semester
        total_units += avg_units_per_semester

    if total_units == 0:
        return 0.0
    return round(total_points / total_units, 2)
