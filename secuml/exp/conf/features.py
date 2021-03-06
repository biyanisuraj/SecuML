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

from enum import Enum

from secuml.core.conf import Conf
from secuml.core.conf import exportFieldMethod
from secuml.core.data.features import FeaturesInfo


class InputFeaturesTypes(Enum):
    file = 0
    dir = 1


class FeaturesConf(Conf):

    def __init__(self, input_features, logger, filter_in_f=None,
                 filter_out_f=None):
        Conf.__init__(self, logger)
        self.input_features = input_features
        self.filter_in_f = filter_in_f
        self.filter_out_f = filter_out_f
        self.input_type = None
        self.set_id = None
        self.files = None
        self.info = None

    def set_input_type(self, input_type):
        self.input_type = input_type

    def set_set_id(self, set_id):
        self.set_id = set_id

    def set_info(self, info):
        self.info = info

    def set_files(self, files):
        self.files = files

    def fields_to_export(self):
        return [('input_features', exportFieldMethod.primitive),
                ('input_type', exportFieldMethod.enum_value),
                ('set_id', exportFieldMethod.primitive),
                ('files', exportFieldMethod.primitive),
                ('info', exportFieldMethod.obj),
                ('filter_in_f', exportFieldMethod.primitive),
                ('filter_out_f', exportFieldMethod.primitive)]

    @staticmethod
    def gen_parser(parser, filters=True):
        group = parser
        if filters:
            group = parser.add_argument_group('Features')
        group.add_argument(
                 '--features', '-f', dest='input_features', required=False,
                 default='features.csv',
                 help='CSV file containing the features or a directory. '
                      'In the latter case, all the files of the directory are '
                      'concatenated to build the input features. '
                      'Default: features.csv. ')
        if filters:
            filter_group = group.add_mutually_exclusive_group()
            filter_group.add_argument(
                             '--filter-in', required=False, default=None,
                             help='File containing the features to use. '
                                  'File format: one feature id per line. ')
            filter_group.add_argument(
                            '--filter-out', required=False, default=None,
                            help='File containing the features to filter out. '
                                 'File format: one feature id per line. ')

    @staticmethod
    def from_args(args, logger):
        if hasattr(args, 'filter_in'):
            filter_in_f = args.filter_in
            filter_out_f = args.filter_out
        else:
            filter_in_f = None
            filter_out_f = None
        return FeaturesConf(args.input_features, logger,
                            filter_in_f=filter_in_f, filter_out_f=filter_out_f)

    @staticmethod
    def from_json(conf_json, logger):
        conf = FeaturesConf(conf_json['input_features'], logger,
                            filter_in_f=conf_json['filter_in_f'],
                            filter_out_f=conf_json['filter_out_f'])
        conf.set_input_type(conf_json['input_type'])
        conf.set_set_id(conf_json['set_id'])
        conf.set_info(FeaturesInfo.from_json(conf_json['info']))
        conf.set_files(conf_json['files'])
        return conf
