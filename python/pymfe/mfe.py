"""Main module for extracting metafeatures from datasets.

Todo:
    * Improve documentation.
    * Implement MFE class.
"""
import typing as t
import collections
import warnings

import numpy as np

import _internal

_TypeSeqExt = t.Sequence[t.Tuple[str, t.Callable, t.Sequence]]
"""Type annotation for a sequence of TypeExtMtdTuple objects."""


class MFE:
    """Core class for metafeature extraction."""
    # pylint: disable=R0902

    def __init__(self,
                 groups: t.Union[str, t.Iterable[str]] = "all",
                 features: t.Union[str, t.Iterable[str]] = "all",
                 summary: t.Union[str, t.Iterable[str]] = ("mean", "sd"),
                 wildcard: str = "all",
                 suppress_warnings: bool = False
                 ) -> None:
        """
        Provides easy access for metafeature extraction from structured
        datasets. It expected that user first calls `fit` method after
        instantiation and then `extract` for effectively extract the se-
        lected metafeatures.

        Attributes:
            groups (:obj:`Iterable` of :obj:`str` or `str`): a collection
                or a single metafeature group name representing the desired
                group of metafeatures for extraction. The supported groups
                are:

                    1. `general`: general/simples metafeatures.
                    2. `statistical`: statistical metafeatures.
                    3. `info-theory`: information-theoretic type of metafea-
                        ture.
                    4. `model-based`: metafeatures based on machine learning
                        model characteristics.
                    5. `landmarking`: metafeatures representing performance
                        metrics from simple machine learning models or machi-
                        ne learning models induced with sampled data.

                The special value provided by the argument `wildcard` can be
                used to rapidly select all metafeature groups.

            features (:obj:`Iterable` of :obj:`str` or `str`, optional): a col-
                lection or a single metafeature name desired for extraction.
                Keep in mind that only features in the selected `groups` will
                be used. Check `feature` attribute in order to get a list of
                available metafeatures from the selected groups.

                The special value provided by the argument `wildcard` can be
                used to rapidly select all features from the selected groups.

            summary (:obj:`Iterable` of :obj:`str` or `str`, optional): a
                collection or a single summary function to summarize a group
                of metafeature measures into a fixed-length group of value,
                typically a single value.

                If more than one summary function is selected, then all multi-
                valued metafeatures extracted will be summarized with each
                summary function.

                The special value provided by the argument `wildcard` can be
                used to rapidly select all summary functions.

            wildcard (:obj:`str`, optional): value used as `select all` for
                `groups`, `features` and `summary` arguments.

            suppress_warnings (:obj:`bool`, optional): if True, than all warn-
                ings invoked at the instantiation time will be ignored.
        """
        # pylint: disable=R0913

        self.groups = _internal.process_groups(groups)  # type: t.Sequence[str]

        self.features, self._ft_mtd_metadata = _internal.process_features(
            features=features,
            groups=self.groups,
            wildcard=wildcard,
            suppress_warnings=suppress_warnings)  \
            # type: t.Tuple[t.Tuple[str, ...], _TypeSeqExt]

        self.summary = _internal.process_summary(
            summary)  # type: t.Sequence[t.Tuple[str, t.Callable, t.Sequence]]

        self.X = None  # type: t.Optional[np.array]
        self.y = None  # type: t.Optional[np.array]

        self.splits = None  # type: t.Optional[t.Iterable[int]]

        self._custom_args_ft = None  # type: t.Optional[t.Dict[str, t.Any]]

    @staticmethod
    def _summarize(features: t.Union[np.ndarray, t.Sequence],
                   callable_sum: t.Callable,
                   callable_args: t.Optional[t.Dict[str, t.Any]],
                   remove_nan: bool = True,
                   ) -> t.Union[t.Sequence, _internal.TypeNumeric]:
        """Returns feature summarized by 'callable_sum'.

        Args:
            features: t.Sequence containing values to summarize.
            callable_sum: t.Callable of the method which implements the desired
                summary function.
            callable_args: arguments to the summary function.
            remove_nan: check and remove all elements in 'features' which are
                not numeric ('int' or 'float' types). Note that :obj:`np.inf`
                is still considered numeric.

        Returns:
            Float value of summarized feature values if possible. May return
            :obj:`np.nan` if summary function call invokes TypeError.

        Raises:
            AttributeError: if 'sum_callable' is invalid.
            TypeError: if 'features' is not a sequence.
        """
        processed_feat = np.array(features)

        if remove_nan:
            numeric_vals = list(map(_internal.isnumeric, features))
            processed_feat = processed_feat[numeric_vals]
            processed_feat = processed_feat.astype(np.float32)

        if callable_args is None:
            callable_args = {}

        try:
            metafeature = callable_sum(processed_feat, **callable_args)

        except TypeError:
            metafeature = np.nan

        return metafeature

    @staticmethod
    def _get_feat_value(method_name: str,
                        method_args: t.Dict[str, t.Any],
                        method_callable: t.Callable,
                        suppress_warnings: bool = False
                        ) -> t.Union[_internal.TypeNumeric, np.ndarray]:
        """Extract feat. from 'method_callable' with 'method_args' as args.

        Args:

        Returns:

        """

        try:
            features = method_callable(**method_args)

        except TypeError as type_e:
            if not suppress_warnings:
                warnings.warn(
                    "Error extracting {0}: \n{1}.\nWill set it "
                    "as 'np.nan' for all summary functions.".format(
                        method_name, repr(type_e)), RuntimeWarning)

            features = np.nan

        return features

    @staticmethod
    def _build_mtd_args(
            method_name: str,
            method_args: t.Iterable[str],
            inner_custom_args: t.Optional[t.Dict[str, t.Any]] = None,
            user_custom_args: t.Optional[t.Dict[str, t.Any]] = None,
            suppress_warnings: bool = False) -> t.Dict[str, t.Any]:
        """Build a 'kwargs' dict for a feature-extraction callable.

        Args:
            method_name: name of the method.
            method_args: Iterable containing the name of all arguments of
                the feature-extraction callable.
            inner_custom_args: custom arguments for inner usage.
            user_custom_args: Dict in the form {'arg': value} given by
                user to customize the given feature-extraction callable.
            suppress_warnings: do not show any warnings about unknown
                parameters.

        Returns:
            A t.Dict which is a ready-to-use kwargs for the correspondent
            callable.
        """

        if user_custom_args is None:
            user_custom_args = {}

        if inner_custom_args is None:
            inner_custom_args = {}

        combined_args = {
            **user_custom_args,
            **inner_custom_args,
        }

        callable_args = {
            custom_arg: combined_args[custom_arg]
            for custom_arg in combined_args if custom_arg in method_args
        }

        if not suppress_warnings:
            unknown_arg_set = (unknown_arg
                               for unknown_arg in user_custom_args.keys()
                               if unknown_arg not in method_args
                               )  # type: t.Generator[str, None, None]

            for unknown_arg in unknown_arg_set:
                warnings.warn(
                    'Unknown argument "{0}" for method "{1}".'.format(
                        unknown_arg, method_name), UserWarning)

        return callable_args

    def fit(self,
            X: t.Sequence,
            y: t.Sequence,
            splits: t.Optional[t.Iterable[int]] = None) -> None:
        """Fits dataset into the MFE model.

        Args:
            X: predictive attributes of the dataset.
            y: target attributes of the dataset.
            splits: iterable which contains K-Fold Cross Validation index
                splits to use mainly in landmarking metafeatures. If not
                given, each metafeature will be extracted a single time.

        Raises:
            ValueError: if number of rows of X and y does not match.
            TypeError: if X or y (or both) is neither a :obj:`list` or
                a :obj:`np.array` object.
        """

        self.X, self.y = _internal.check_data(X, y)

        if (splits is not None
                and not isinstance(splits, collections.Iterable)):
            raise TypeError('"splits" argument must be a iterable.')

        self.splits = splits

        self._custom_args_ft = {
            "X": self.X,
            "y": self.y,
            "splits": self.splits,
        }

    @staticmethod
    def _check_summary_warnings(
            value: t.Union[_internal.TypeNumeric, t.Sequence, np.ndarray],
            name_feature: str,
            name_summary: str) -> None:
        """Check if there's :obj:`np.nan` within summarized values.

        Args:

        Returns:
        """

        if not isinstance(value, collections.Iterable):
            value = [value]

        if any(np.isnan(value)):
            warnings.warn(
                "Failed to summarize {0} with {1}. "
                "(generated NaN).".format(name_feature,
                                          name_summary), RuntimeWarning)

    def _call_summary_methods(
                self,
                feature_values: t.Sequence[_internal.TypeNumeric],
                feature_name: str,
                remove_nan: bool = True,
                suppress_warnings: bool = False,
                **kwargs
                ) -> t.Tuple[t.List[str], t.List[t.Union[float, t.Sequence]]]:
        """Invoke summary functions loaded in model on given feature values.

        Args:

        Returns:
        """
        metafeat_vals = []  # type: t.List[t.Union[int, float, t.Sequence]]
        metafeat_names = []  # type: t.List[str]

        for sm_mtd_name, sm_mtd_callable, sm_mtd_args in self.summary:

            sm_mtd_args_pack = MFE._build_mtd_args(
                method_name=sm_mtd_name,
                method_args=sm_mtd_args,
                user_custom_args=kwargs.get(sm_mtd_name),
                inner_custom_args=None,
                suppress_warnings=suppress_warnings)

            summarized_val = MFE._summarize(
                features=feature_values,
                callable_sum=sm_mtd_callable,
                callable_args=sm_mtd_args_pack,
                remove_nan=remove_nan)

            if not suppress_warnings:
                MFE._check_summary_warnings(
                    value=summarized_val,
                    name_feature=feature_name,
                    name_summary=sm_mtd_name)

            metafeat_vals.append(summarized_val)
            metafeat_names.append("{0}.{1}".format(
                feature_name, sm_mtd_name))

        return metafeat_names, metafeat_vals

    def extract(self,
                remove_nan: bool = True,
                suppress_warnings: bool = False,
                **kwargs
                ) -> t.Tuple[t.List[str], t.List[t.Union[float, t.Sequence]]]:
        """Extracts metafeatures from previously fitted dataset.

        Args:
            remove_nan: if True, remove any non-numeric values features
                before summarizing then.
            suppress_warnings: do not show warnings about unknown user
                custom parameters.

        Returns:
            t.List containing all metafeatures summarized by all summary
            functions loaded in the model.

        Raises:
            TypeError: if calling 'extract' method before 'fit' method.
        """
        if self.X is None or self.y is None:
            raise TypeError("Fitted data not found. Call "
                            '"fit" method before "extract".')

        if (not isinstance(self.X, np.ndarray)
                or not isinstance(self.y, np.ndarray)):
            self.X, self.y = _internal.check_data(self.X, self.y)

        metafeat_vals = []  # type: t.List[t.Union[int, float, t.Sequence]]
        metafeat_names = []  # type: t.List[str]

        for ft_mtd_name, ft_mtd_callable, ft_mtd_args in self._ft_mtd_metadata:

            ft_name_without_prefix = _internal.remove_mtd_prefix(ft_mtd_name)

            ft_mtd_args_pack = MFE._build_mtd_args(
                method_name=ft_name_without_prefix,
                method_args=ft_mtd_args,
                user_custom_args=kwargs.get(ft_name_without_prefix),
                inner_custom_args=self._custom_args_ft,
                suppress_warnings=suppress_warnings)

            features = MFE._get_feat_value(
                ft_mtd_name,
                ft_mtd_args_pack,
                ft_mtd_callable,
                suppress_warnings)

            if isinstance(features, (np.ndarray, collections.Sequence)):
                summarized_names, summarized_vals = self._call_summary_methods(
                    feature_values=features,
                    feature_name=ft_name_without_prefix,
                    remove_nan=remove_nan,
                    suppress_warnings=suppress_warnings,
                    **kwargs)

                metafeat_vals += summarized_vals
                metafeat_names += summarized_names

            else:
                metafeat_vals.append(features)
                metafeat_names.append(ft_name_without_prefix)

        return metafeat_names, metafeat_vals


if __name__ == "__main__":
    attr = np.array([
        [1, 2, 3, 4],
        [0, 0, 1, 1],
        [1, 2, 1, 1],
        [1, 1, 1, 1],
    ])

    labels = np.array([1, 1, 0, 0])

    MODEL = MFE(groups="all", features="all")
    print(MODEL.features)
    MODEL.fit(X=attr, y=labels)
    names, vals = MODEL.extract(
        suppress_warnings=False,
        remove_nan=True, **{"sd": {"ddof": 1}})

    for n, v in zip(names, vals):
        print(n, v)
