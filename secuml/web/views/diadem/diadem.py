# SecuML
# Copyright (C) 2016-2019  ANSSI
#
# SecuML is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# SecuML is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with SecuML. If not, see <http://www.gnu.org/licenses/>.

from flask import render_template, send_file, jsonify
import numpy as np
import os.path as path
from sklearn.externals import joblib
from sqlalchemy.orm.exc import NoResultFound

from secuml.web import app, secuml_conf, session
from secuml.web.views.experiments import update_curr_exp

from secuml.core.tools.plots.barplot import BarPlot
from secuml.core.tools.plots.dataset import PlotDataset
from secuml.core.tools.color import red

from secuml.exp.diadem import DiademExp  # NOQA
from secuml.exp.data.features import FeaturesFromExp
from secuml.exp.tools.db_tables import call_specific_db_func
from secuml.exp.tools.db_tables import DiademExpAlchemy
from secuml.exp.tools.db_tables import ExpAlchemy
from secuml.exp.tools.db_tables import ExpRelationshipsAlchemy
from secuml.exp.tools.db_tables import GroundTruthAlchemy
from secuml.exp.tools.db_tables import InstancesAlchemy
from secuml.exp.tools.db_tables import PredictionsAlchemy

TOP_N_ALERTS = 100


def db_row_to_json(row):
    return {c.name: getattr(row, c.name) for c in row.__table__.columns}


@app.route('/getDiademChildInfo/<exp_id>/')
def getDiademChildInfo(exp_id):
    query = session.query(DiademExpAlchemy)
    query = query.filter(DiademExpAlchemy.exp_id == exp_id)
    return jsonify(db_row_to_json(query.one()))


@app.route('/getDiademDetectionChildExp/<diadem_exp_id>/<child_type>/'
           '<fold_id>/')
def getDiademDetectionChildExp(diadem_exp_id, child_type, fold_id):
    fold_id = None if fold_id == 'None' else int(fold_id)
    query = session.query(DiademExpAlchemy)
    if child_type != 'cv':
        query = query.join(DiademExpAlchemy.exp)
        query = query.join(ExpAlchemy.parents)
        query = query.filter(ExpAlchemy.kind == 'Detection')
        query = query.filter(
                            ExpRelationshipsAlchemy.parent_id == diadem_exp_id)
    else:
        query = query.filter(DiademExpAlchemy.exp_id == diadem_exp_id)
    query = query.filter(DiademExpAlchemy.type == child_type)
    query = query.filter(DiademExpAlchemy.fold_id == fold_id)
    return jsonify(db_row_to_json(query.one()))


@app.route('/getDiademTrainChildExp/<diadem_exp_id>/<fold_id>/<child_type>/')
def getDiademTrainChildExp(diadem_exp_id, fold_id, child_type):
    fold_id = None if fold_id == 'None' else int(fold_id)
    query = session.query(DiademExpAlchemy)
    if child_type != 'cv':
        query = query.join(DiademExpAlchemy.exp)
        query = query.join(ExpAlchemy.parents)
        query = query.filter(ExpAlchemy.kind == 'Train')
        query = query.filter(
                            ExpRelationshipsAlchemy.parent_id == diadem_exp_id)
    else:
        query = query.filter(DiademExpAlchemy.exp_id == diadem_exp_id)
    query = query.filter(DiademExpAlchemy.type == child_type)
    query = query.filter(DiademExpAlchemy.fold_id == fold_id)
    return jsonify(db_row_to_json(query.one()))


@app.route('/getDiademExp/<exp_id>/')
def getDiademExp(exp_id):
    query = session.query(DiademExpAlchemy)
    query = query.filter(DiademExpAlchemy.exp_id == exp_id)
    return jsonify(db_row_to_json(query.one()))


@app.route('/predictionsAnalysis/<train_exp_id>/<index>/')
def predictionsAnalysis(train_exp_id, index):
    exp = update_curr_exp(train_exp_id)
    return render_template('diadem/predictions.html',
                           project=exp.exp_conf.dataset_conf.project)


@app.route('/alerts/<exp_id>/<analysis_type>/')
def displayAlerts(exp_id, analysis_type):
    experiment = update_curr_exp(exp_id)
    return render_template('diadem/alerts.html',
                           project=experiment.exp_conf.dataset_conf.project)


@app.route('/errors/<exp_id>/<error_kind>/')
def displayErrors(exp_id, error_kind):
    experiment = update_curr_exp(exp_id)
    return render_template('diadem/errors.html',
                           project=experiment.exp_conf.dataset_conf.project)


@app.route('/getAlertsClusteringExpId/<test_exp_id>/')
def getAlertsClusteringExpId(test_exp_id):
    query = session.query(ExpRelationshipsAlchemy)
    query = query.join(ExpRelationshipsAlchemy.child)
    query = query.join(ExpAlchemy.diadem_exp)
    query = query.filter(ExpRelationshipsAlchemy.parent_id == test_exp_id)
    query = query.filter(DiademExpAlchemy.type == 'alerts')
    try:
        return str(query.one().child_id)
    except NoResultFound:
        return 'None'


@app.route('/getAlerts/<exp_id>/<analysis_type>/')
def getAlerts(exp_id, analysis_type):
    exp = update_curr_exp(exp_id)
    # With proba ?
    query = session.query(DiademExpAlchemy)
    query = query.filter(DiademExpAlchemy.exp_id == exp_id)
    with_proba = query.one().proba
    threshold = None
    if with_proba:
        threshold = exp.exp_conf.core_conf.detection_threshold
    # Get alerts
    query = session.query(PredictionsAlchemy)
    query = query.filter(PredictionsAlchemy.exp_id == exp_id)
    if with_proba:
        query = query.filter(PredictionsAlchemy.proba >= threshold)
    if analysis_type == 'topN' and with_proba:
        query = query.order_by(PredictionsAlchemy.proba.desc())
    elif analysis_type == 'random':
        query = call_specific_db_func(secuml_conf.db_type, 'random_order',
                                      (query,))
    query = query.limit(TOP_N_ALERTS)
    predictions = query.all()
    if predictions:
        ids, probas = zip(*[(r.instance_id, r.proba) for r in predictions])
    else:
        ids = []
        probas = []
    return jsonify({'instances': ids, 'proba': probas})


@app.route('/getPredictionsProbas/<exp_id>/<index>/<label>/')
def getPredictionsProbas(exp_id, index, label):
    index = int(index)
    proba_min = index * 0.1
    proba_max = (index + 1) * 0.1
    query = session.query(PredictionsAlchemy)
    query = query.filter(PredictionsAlchemy.exp_id == exp_id)
    query = query.filter(PredictionsAlchemy.proba >= proba_min)
    query = query.filter(PredictionsAlchemy.proba <= proba_max)
    if label != 'all':
        query = query.join(PredictionsAlchemy.instance)
        query = query.join(InstancesAlchemy.ground_truth)
        query = query.filter(GroundTruthAlchemy.label == label)
    predictions = query.all()
    if predictions:
        ids, probas = zip(*[(r.instance_id, r.proba) for r in predictions])
    else:
        ids = []
        probas = []
    return jsonify({'instances': ids, 'proba': probas})


@app.route('/getPredictions/<exp_id>/<predicted_value>/<right_wrong>/'
           '<multiclass>/')
def getPredictions(exp_id, predicted_value, right_wrong, multiclass):
    query = session.query(PredictionsAlchemy)
    query = query.filter(PredictionsAlchemy.exp_id == exp_id)
    query = query.filter(PredictionsAlchemy.value == predicted_value)
    if right_wrong != 'all':
        query = query.join(PredictionsAlchemy.instance)
        query = query.join(InstancesAlchemy.ground_truth)
        field = 'family' if multiclass else 'label'
        if right_wrong == 'right':
            query = query.filter(getattr(GroundTruthAlchemy, field) ==
                                 predicted_value)
        elif right_wrong == 'wrong':
            query = query.filter(getattr(GroundTruthAlchemy, field) !=
                                 predicted_value)
        else:
            assert(False)
    predictions = query.all()
    if predictions:
        ids, probas = zip(*[(r.instance_id, r.proba) for r in predictions])
    else:
        ids = []
        probas = []
    return jsonify({'instances': ids, 'proba': probas})


@app.route('/supervisedLearningMonitoring/<exp_id>/<kind>/')
def supervisedLearningMonitoring(exp_id, kind):
    exp = update_curr_exp(exp_id)
    filename = kind
    if kind in ['ROC', 'false_discovery_recall_curve']:
        filename += '.png'
    else:
        filename += '.json'
    return send_file(path.join(exp.output_dir(), filename))


@app.route('/predictionsInterpretation/<exp_id>/')
def predictionsInterpretation(exp_id):
    query = session.query(DiademExpAlchemy)
    query = query.filter(DiademExpAlchemy.exp_id == exp_id)
    # first() and not one()
    # because a train experiment can be shared by several DIADEM experiments.
    return str(query.first().pred_interp)


def get_train_exp(exp_id):
    query = session.query(DiademExpAlchemy)
    query = query.filter(DiademExpAlchemy.exp_id == exp_id)
    row = query.one()
    if row.type == 'train':
        return exp_id
    elif row.type == 'test':
        # get diadem_exp
        query = session.query(ExpRelationshipsAlchemy)
        query = query.filter(ExpRelationshipsAlchemy.child_id == exp_id)
        diadem_exp_id = query.one().parent_id
        # get train_exp
        query = session.query(DiademExpAlchemy)
        query = query.join(DiademExpAlchemy.exp)
        query = query.join(ExpAlchemy.parents)
        query = query.filter(
                ExpRelationshipsAlchemy.parent_id == diadem_exp_id)
        query = query.filter(DiademExpAlchemy.fold_id == row.fold_id)
        query = query.filter(DiademExpAlchemy.type == 'train')
        return query.one().exp_id
    else:
        assert(False)


def get_classifier(exp_id):
    train_exp_id = get_train_exp(exp_id)
    train_exp = update_curr_exp(train_exp_id)
    return joblib.load(path.join(train_exp.output_dir(), 'model.out'))


@app.route('/getTopWeightedFeatures/<exp_id>/<instance_id>/<size>/')
def getTopWeightedFeatures(exp_id, instance_id, size):
    instance_id = int(instance_id)
    classifier = get_classifier(exp_id)
    # get the features
    exp = update_curr_exp(exp_id)
    f_names, f_values = FeaturesFromExp.get_instance(exp, instance_id)
    # scale the features
    scaled_values = classifier.named_steps['scaler'].transform(np.reshape(
                                                    f_values, (1, -1)))
    weighted_values = np.multiply(scaled_values,
                                  classifier.named_steps['model'].coef_)
    features = list(map(lambda name, value, w_value: (name, value, w_value),
                        f_names, f_values, weighted_values[0]))
    features.sort(key=lambda tup: abs(tup[2]))
    features = features[:-int(size) - 1:-1]
    f_names, f_values, f_weighted = list(zip(*features))
    labels = [str(name) for name in f_names]
    tooltips = ['%s (%.2f)' % (name, f_values[i])
                for i, name in enumerate(f_names)]
    barplot = BarPlot(labels)
    dataset = PlotDataset(f_weighted, None)
    dataset.set_color(red)
    barplot.add_dataset(dataset)
    return jsonify(barplot.to_json(tooltip_data=tooltips))
