"""Provides useful functions for MFE package.

Attributes:
    VALID_GROUPS (:obj:`tuple` of :obj:`str`): Supported groups of
        metafeatures of pymfe.

    VALID_SUMMARY (:obj:`tuple` of :obj:`str`): Supported summary
        functions to combine metafeature values.

    VALID_MFECLASSES (:obj:`tuple` of Classes): Metafeature ex-
        tractors predefined classes, where metafeature-extraction
        methods will be searched.

    MTF_PREFIX (:obj:`str`): prefix of metafeature-extraction me-
        thod names. For example, the metafeature called `inst_nr`
        is implemented in the method named `[MTF_PREFIX]_inst_nr`.
"""
import typing as t
import inspect
import collections
import operator
import warnings

import numpy as np

import _summary
import general
import statistical
import info_theory
import landmarking
import model_based

VALID_GROUPS = (
    "landmarking",
    "general",
    "statistical",
    "model-based",
    "info-theory",
)  # type: t.Tuple[str, ...]

VALID_SUMMARY = (*_summary.SUMMARY_METHODS, )  # type: t.Tuple[str, ...]

VALID_MFECLASSES = (
    landmarking.MFELandmarking,
    general.MFEGeneral,
    statistical.MFEStatistical,
    model_based.MFEModelBased,
    info_theory.MFEInfoTheory,
)  # type: t.Tuple

MTF_PREFIX = "ft_"
"""Prefix which is that metafeat. extraction related methods starts with."""

TypeMtdTuple = t.Tuple[str, t.Callable[[], t.Any]]
"""Type annotation which describes the a metafeature method tuple."""

TypeExtMtdTuple = t.Tuple[str, t.Callable[[], t.Any], t.Sequence]
"""Type annotation which extends TypeMtdTuple with extra field (for 'Args')"""

_TYPE_NUMERIC = (
    int,
    float,
    np.int32,
    np.float32,
    np.float64,
    np.int64,
)

TypeNumeric = t.TypeVar(
    "TypeNumeric",
    int,
    float,
    np.int32,
    np.float32,
    np.float64,
    np.int64,
)
"""Typing alias for both numeric types."""


def _check_value_in_group(value: t.Union[str, t.Iterable[str]],
                          group: t.Iterable[str],
                          wildcard: str = "all"
                          ) -> t.Tuple[t.Tuple[str, ...], t.Tuple[str, ...]]:
    """Checks if a value is in a set or a set of values is a subset of a set.

    Args:
        value (:obj:`Iterable` of :obj:`str` or :obj:`str): value(s) to be
            checked if are in the given group of strings.

        group (:obj:`Iterable` of :obj:`str`): a group of strings represen-
            ting the values such that `value` will be verified against.

        wildcard (:obj:`str`, optional): a value which represent 'all values'.
            The case is ignored, so, for example, both values 'all', 'ALL' and
            any mix of cases are considered to be the same wildcard token.

    Returns:
        tuple(tuple, tuple): A pair of tuples containing, respectively, values
        that are in the given group and those that are not. If no value is in
        either group, then this group will be None.

    Raises:
        TypeError: if `value` is not a Iterable type or some of its elements
            are not a :obj:`str` type.
    """

    if not isinstance(value, collections.Iterable):
        raise TypeError("Parameter type is not "
                        "consistent ({0}).".format(type(value)))

    in_group = tuple()  # type: t.Tuple[str, ...]
    not_in_group = tuple()  # type: t.Tuple[str, ...]

    if isinstance(value, str):
        value = value.lower()
        if value == wildcard.lower():
            in_group = tuple(group)

        elif value in group:
            in_group = (value, )

        else:
            not_in_group = (value, )

    else:
        value_set = set(map(str.lower, value))

        if wildcard.lower() in value_set:
            in_group = tuple(group)

        else:
            in_group = tuple(value_set.intersection(group))
            not_in_group = tuple(value_set.difference(group))

    return in_group, not_in_group


def process_groups(groups: t.Union[t.Iterable[str], str]) -> t.Tuple[str, ...]:
    """Process `groups` argument from MFE.__init__ to generate internal metadata.

    Args:
        groups (:obj:`str` or :obj:`t.Iterable` of :obj:`str`): a single
            string or a iterable with group identifiers to be processed.
            It must assume or contain the following values:
                1. `landmarking`: Landmarking metafeatures.
                2. `general`: General/simple metafeatures.
                3. `statistical`: Statistical metafeatures.
                4. `model-based`: Metafeatures from machine learning models.
                5. `info-theory`: Information Theory metafeatures.

    Returns:
        tuple(str): containing all valid group lower-cased identifiers.

    Raises:
        TypeError: if `groups` is neither a string `all` nor a Iterable
            containing valid group identifiers as strings.

        ValueError: if `groups` is None or is a empty Iterable or if a unknown
            group identifier is given.
    """
    if not groups:
        raise ValueError('"Groups" can not be None nor empty.')

    in_group, not_in_group = _check_value_in_group(groups, VALID_GROUPS)

    if not_in_group:
        raise ValueError(
            "Unknown groups: {0}. "
            "Please select values in {1}.".format(not_in_group, VALID_GROUPS))

    return in_group


def process_summary(
        summary: t.Union[str, t.Iterable[str]]
        ) -> t.Tuple[t.Tuple[str, ...], t.Tuple[TypeExtMtdTuple, ...]]:
    """Process `summary` argument from MFE.__init__ to generate internal metadata.

    Args:
        summary (:obj:`t.Iterable` of :obj:`str` or a :obj:`str`): a
            summary function or a list of these, which are used to
            combine different calculations of the same metafeature. Check
            ``MFE`` Class documentation for more information about this
            parameter.

    Returns:
        tuple(tuple, tuple): the first field contains all valid lower-cased
            summary function names, where the last field contains internal
            metadata about methods which implements each summary function.
            This last tuple model is:

                (
                    `summary_mtd_name`,
                    `summary_mtd_callable`,
                    `summary_mtd_args`,
                )

    Raises:
        TypeError: if `summary` is neither a string `all` nor a Iterable
            containing valid group identifiers as strings.

        ValueError: if `summary` is None or is a empty Iterable or if a un-
            known group identifier is given.
    """
    if not summary:
        raise ValueError('"Summary" can not be None nor empty.')

    in_group, not_in_group = _check_value_in_group(summary, VALID_SUMMARY)

    if not_in_group:
        raise ValueError(
            "Unknown summary: {0}. "
            "Please select values in {1}.".format(not_in_group, VALID_SUMMARY))

    summary_methods = []  # type: t.List[TypeExtMtdTuple]
    available_sum_methods = []  # type: t.List[str]

    for summary_func in in_group:
        summary_mtd_callable = _summary.SUMMARY_METHODS[summary_func]

        try:
            summary_mtd_args = _extract_mtd_args(summary_mtd_callable)

        except ValueError:
            summary_mtd_args = []

        summary_mtd_pack = (
            summary_func,
            summary_mtd_callable,
            summary_mtd_args,
        )

        summary_methods.append(summary_mtd_pack)
        available_sum_methods.append(summary_func)

    return tuple(available_sum_methods), tuple(summary_methods)


def check_data(X: t.Union[np.ndarray, list], y: t.Union[np.ndarray, list]
               ) -> t.Tuple[np.ndarray, np.ndarray]:
    """Checks received `X` and `y` data type and shape.

    Args:
        Check `mfe.fit` method for more information.

    Raises:
        TypeError: if `X` or `y` is neither a np.ndarray nor a list-
        type object.

    Returns:
        tuple(np.ndarray, np.ndarray): X and y possibly reshaped and
        casted to np.ndarray type.
    """
    if not isinstance(X, (np.ndarray, list)):
        raise TypeError('"X" is neither "list" nor "np.array".')

    if not isinstance(y, (np.ndarray, list)):
        raise TypeError('"y" is neither "list" nor "np.array".')

    if not isinstance(X, np.ndarray):
        X = np.array(X)

    if not isinstance(y, np.ndarray):
        y = np.array(y)

    y = y.flatten()

    if len(X.shape) == 1:
        X = X.reshape(*X.shape, -1)

    if X.shape[0] != y.shape[0]:
        raise ValueError('"X" number of rows and "y" '
                         "length shapes do not match.")

    return X, y


def _get_feat_mtds_from_class(class_obj: t.Callable) -> t.List[TypeMtdTuple]:
    """Get feature-extraction related methods from a given MFE Class.

    Is assumed that methods related with feature extraction are prefixed
    with :obj:`MTF_PREFIX` value.

    Args:
        class_obj (:obj:`Class`): Class from which the feature methods
            should be extracted.

    Returns:
        list(tuple): a list of tuples in the form (`mtd_name`,
        `mtd_address`) which contains all methods associated with
        feature extraction (prefixed with :obj:`MTF_PREFIX`).
    """
    feature_mtd_list = inspect.getmembers(
        class_obj,
        predicate=inspect.ismethod)  # type: t.List[TypeMtdTuple]

    # It is assumed that all feature-extraction related methods
    # name are all prefixed with "MTF_PREFIX".
    feature_mtd_list = [
        ft_method for ft_method in feature_mtd_list
        if ft_method[0].startswith(MTF_PREFIX)
    ]

    return feature_mtd_list


def _get_all_ft_mtds() -> t.Dict[str, t.List[TypeMtdTuple]]:
    """Get all feature-extraction related methods in prefefined Classes.

    Feature-extraction methods are prefixed with :obj:`MTF_PREFIX` from all
    Classes predefined in :obj:`VALID_MFECLASSES` tuple.

    Returns:
        dict: in the form {`group_name`: [(`mtd_name`, `mtd_address`)]},
        i.e. the keys are the names of feature groups (e.g. `general` or
        `landmarking`) and values are lists of tuples which first entry are
        feature-extraction related method names and the second entry are its
        correspondent address. For example:

            {
                `general`: [
                    (`ft_nr_num`, <mtd_address>),
                    (`ft_nr_inst`, <mtd_address>),
                    ...
                ],

                `statistical`: [
                    (`ft_mean`, <mtd_address>),
                    (`ft_max`, <mtd_address>),
                    ...
                ],

                ...
            }
    """
    feature_mtd_dict = {
        ft_type_id: _get_feat_mtds_from_class(mfe_class)
        for ft_type_id, mfe_class in zip(VALID_GROUPS, VALID_MFECLASSES)
    }  # type: t.Dict[str, t.List[TypeMtdTuple]]

    return feature_mtd_dict


def _filter_mtd_dict(
        ft_mtds_dict: t.Dict[str, t.List[TypeMtdTuple]],
        groups: t.Optional[t.Tuple[str, ...]]) -> t.Tuple[TypeMtdTuple]:
    """Filter return of `_get_all_ft_mtds(...)` function based on given `groups`.

    This is an auxiliary function for `process_features(...)` function.

    Args:
        ft_mtds_dict (:obj:`Dict`): return from `_get_all_ft_mtds(...)`
            function.

        groups (:obj:`Tuple` of :obj:`str`): a tuple of feature group names. It
        can assume value :obj:`None`, which is interpreted as ``no filter``
        (i.e. all features of all groups will be returned).

    Returns:
        tuple(str): containing only values of input `ft_mtds_dict` related
        to the given `groups`.
    """

    if groups:
        groups = tuple(set(groups).intersection(ft_mtds_dict.keys()))

        ft_mtds_filtered = operator.itemgetter(*groups)(ft_mtds_dict)

        if len(groups) == 1:
            ft_mtds_filtered = (ft_mtds_filtered, )

    else:
        ft_mtds_filtered = tuple(ft_mtds_dict.values())

    ft_mtds_filtered = tuple(mtd_tuple for ft_group in ft_mtds_filtered
                             for mtd_tuple in ft_group)

    return ft_mtds_filtered


def _preprocess_ft_arg(
        features: t.Union[str, t.Iterable[str]]) -> t.Union[str, t.List[str]]:
    """Process `features` to a canonical form.

    Remove repeated elements from a collection of features and cast all values
    to lower-case.

    Args:
        features (:obj:`Iterable` of :obj:`str` or :obj:`str`): feature names
            or a collection of to be processed into a lower-case form.

    Returns:
        list(str) or str: the return type is a string if `features` is string
            type or a list if `features` is a iterable. The values are strings
            all lower-cased.
    """
    if not isinstance(features, str):
        return list(map(str.lower, set(features)))

    return features.lower()


def _extract_mtd_args(ft_mtd_callable: t.Callable) -> t.List[str]:
    """Extracts arguments from given method.

    Args:
        ft_mtd_callable (:obj:`Callable`): a callable related to a feature
            extraction method.

    Returns:
        list(str): containing the name of arguments of `ft_mtd_callable`.

    Raises:
        TypeError: if 'ft_mtd_callable' is not a valid Callable.
    """
    ft_mtd_signature = inspect.signature(ft_mtd_callable)
    mtd_callable_args = list(ft_mtd_signature.parameters.keys())
    return mtd_callable_args


def _check_ft_wildcard(
        features: t.Union[str, t.Iterable[str]],
        ft_methods: t.Sequence[TypeMtdTuple],
        wildcard: str = "all"
        ) -> t.Optional[t.Tuple[t.Tuple[str, ...],
                                t.Tuple[TypeExtMtdTuple, ...]]]:
    """Returns all features if feature wildcard matches, None otherwise.

    Args:
        features: a feature or a t.Iterable with feature names.
        ft_methods: t.Sequence containing tuples in the form
            ('mtd_name', 'mtd_callable).
    """

    if (isinstance(features, str) and features.lower() == wildcard.lower()):

        ext_ft_methods = tuple((mtd_name, mtd_callable,
                                _extract_mtd_args(mtd_callable))
                               for mtd_name, mtd_callable in ft_methods)

        all_ft_names = tuple((
            remove_mtd_prefix(mtd_name)
            for mtd_name, _ in ft_methods))

        return all_ft_names, ext_ft_methods

    return None


def _process_features_warnings(unknown_feats: t.Sequence[str]) -> None:
    """Warns for unknown features detected in 'process_features' function."""
    if not isinstance(unknown_feats, str):
        for unknown_ft in unknown_feats:
            warnings.warn('Unknown feature "{0}"'.format(unknown_ft),
                          UserWarning)
    else:
        warnings.warn('Unknown feature "{0}"'.format(unknown_feats),
                      UserWarning)


def process_features(
        features: t.Union[str, t.Iterable[str]],
        groups: t.Optional[t.Tuple[str, ...]] = None,
        wildcard: str = "all",
        suppress_warnings=False
        ) -> t.Tuple[t.Tuple[str, ...], t.Tuple[TypeExtMtdTuple, ...]]:
    """Check if 'features' argument from MFE.__init__ is correct.

    This function is expected to be used after 'process_groups' method.

    Args:
        features: t.Iterable containing a group of features or a string
            containing a single feature. Note that only features that
            are in the given 'groups' will be returned.
        groups: t.Sequence containing one or more group identifiers.
        wildcard: value to be used as 'select all features' for 'features'
            argument.

    Returns:
        A tuple containing tuples in the following format:

            ('mtd_name', 'mtd_callable')

        i.e., the first tuple item field is a string containing the name
        of a feature-extraction related method, and the second field is
        a callable object for the corresponding method.
    """

    if not features:
        return tuple(), tuple()

    processed_ft = _preprocess_ft_arg(
        features)  # type: t.Union[str, t.List[str]]

    ft_mtds_filtered = _filter_mtd_dict(
        _get_all_ft_mtds(), groups)  # type: t.Sequence[TypeMtdTuple]

    all_features_ret = _check_ft_wildcard(
        features=processed_ft,
        ft_methods=ft_mtds_filtered,
        wildcard=wildcard)

    if all_features_ret:
        return all_features_ret

    available_feat_names = []  # type: t.List[str]
    ft_mtd_processed = []  # type: t.List[TypeExtMtdTuple]

    for ft_mtd_tuple in ft_mtds_filtered:
        ft_mtd_name, ft_mtd_callable = ft_mtd_tuple

        mtd_name_without_prefix = remove_mtd_prefix(ft_mtd_name)

        mtd_callable_args = _extract_mtd_args(ft_mtd_callable)

        extended_item = (*ft_mtd_tuple,
                         mtd_callable_args)  # type: TypeExtMtdTuple

        if not isinstance(processed_ft, str):
            if mtd_name_without_prefix in processed_ft:
                ft_mtd_processed.append(extended_item)
                available_feat_names.append(mtd_name_without_prefix)
                processed_ft.remove(mtd_name_without_prefix)

        else:
            # In this case, user is only interested in a single
            # metafeature
            if mtd_name_without_prefix == processed_ft:
                return (mtd_name_without_prefix, ), (extended_item, )

    if not suppress_warnings:
        _process_features_warnings(processed_ft)

    return tuple(available_feat_names), tuple(ft_mtd_processed)


def isnumeric(value: t.Any) -> bool:
    """Checks if 'x' is a Numeric Type."""
    return isinstance(value, _TYPE_NUMERIC)


def remove_mtd_prefix(mtd_name: str) -> str:
    """Remove feature-extraction method prefix from its name."""
    if mtd_name.startswith(MTF_PREFIX):
        return mtd_name[len(MTF_PREFIX):]

    return mtd_name
