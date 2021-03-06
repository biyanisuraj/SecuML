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

from sklearn.externals import joblib
import os.path as path

from .interp.coeff import Coefficients


class ClassifierMonitoring(object):

    def __init__(self, exp, num_folds=1):
        self.exp = exp
        self.num_folds = num_folds
        self.pipelines = [None for _ in range(self.num_folds)]
        self.exec_time = 0
        self.coefficients = None

    def set_classifier(self, classifier, exec_time, fold_id=0):
        self.pipelines[fold_id] = classifier.pipeline
        self.exec_time += exec_time
        self.set_coefficients(classifier, fold_id)

    def set_coefficients(self, classifier, fold_id):
        coefs = classifier.get_coefs()
        if coefs is not None:
            if self.coefficients is None:
                self.coefficients = Coefficients(self.exp, classifier.conf,
                                                 num_folds=self.num_folds)
            self.coefficients.add_fold(coefs, fold_id=fold_id)

    def final_computations(self):
        if self.coefficients is not None:
            self.coefficients.final_computations()

    def display(self, directory):
        self._export_pipelines(directory)
        if self.coefficients is not None:
            self.coefficients.display(directory)

    def _export_pipelines(self, directory):
        if self.num_folds == 1:
            joblib.dump(self.pipelines[0], path.join(directory, 'model.out'))
        else:
            for fold_id, pipeline in enumerate(self.pipelines):
                joblib.dump(pipeline, path.join(directory,
                                                'model_%i.out' % fold_id))
