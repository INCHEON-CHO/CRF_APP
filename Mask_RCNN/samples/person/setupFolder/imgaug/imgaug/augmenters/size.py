"""
Augmenters that somehow change the size of the images.

Do not import directly from this file, as the categorization is not final.
Use instead ::

    from imgaug import augmenters as iaa

and then e.g. ::

    seq = iaa.Sequential([
        iaa.Resize({"height": 32, "width": 64})
        iaa.Crop((0, 20))
    ])

List of augmenters:

    * Resize
    * CropAndPad
    * Crop
    * Pad
    * PadToFixedSize
    * CropToFixedSize
    * KeepSizeByResize

"""
from __future__ import print_function, division, absolute_import

import re

import numpy as np
import six.moves as sm

from . import meta
import imgaug as ia
from .. import parameters as iap


def _int_r(value):
    return int(np.round(value))


# TODO somehow integrate this with ia.pad()
def _handle_pad_mode_param(pad_mode):
    pad_modes_available = {
        "constant", "edge", "linear_ramp", "maximum", "mean", "median",
        "minimum", "reflect", "symmetric", "wrap"}
    if pad_mode == ia.ALL:
        return iap.Choice(list(pad_modes_available))
    elif ia.is_string(pad_mode):
        assert pad_mode in pad_modes_available, (
            "Value '%s' is not a valid pad mode. Valid pad modes are: %s." % (
                pad_mode, ", ".join(pad_modes_available)))
        return iap.Deterministic(pad_mode)
    elif isinstance(pad_mode, list):
        assert all([v in pad_modes_available for v in pad_mode]), (
            "At least one in list %s is not a valid pad mode. Valid pad "
            "modes are: %s." % (str(pad_mode), ", ".join(pad_modes_available)))
        return iap.Choice(pad_mode)
    elif isinstance(pad_mode, iap.StochasticParameter):
        return pad_mode
    raise Exception(
        "Expected pad_mode to be ia.ALL or string or list of strings or "
        "StochasticParameter, got %s." % (type(pad_mode),))


def _crop_prevent_zero_size(height, width, crop_top, crop_right, crop_bottom,
                            crop_left):
    remaining_height = height - (crop_top + crop_bottom)
    remaining_width = width - (crop_left + crop_right)
    if remaining_height < 1:
        regain = abs(remaining_height) + 1
        regain_top = regain // 2
        regain_bottom = regain // 2
        if regain_top + regain_bottom < regain:
            regain_top += 1

        if regain_top > crop_top:
            diff = regain_top - crop_top
            regain_top = crop_top
            regain_bottom += diff
        elif regain_bottom > crop_bottom:
            diff = regain_bottom - crop_bottom
            regain_bottom = crop_bottom
            regain_top += diff

        assert regain_top <= crop_top, (
            "Failed to get regain_top<=crop_top for height %d, width %d, "
            "crop_top %d, crop_right %d, crop_bottom %d, crop_left %d,"
            "regain_top %d." % (
                height, width, crop_top, crop_right, crop_bottom, crop_left,
                regain_top))
        assert regain_bottom <= crop_bottom, (
            "Failed to get regain_bottom<=crop_bottom for height %d, width "
            "%d, crop_top %d, crop_right %d, crop_bottom %d, crop_left %d,"
            "regain_bottom %d." % (
                height, width, crop_top, crop_right, crop_bottom, crop_left,
                regain_bottom))

        crop_top = crop_top - regain_top
        crop_bottom = crop_bottom - regain_bottom

    if remaining_width < 1:
        regain = abs(remaining_width) + 1
        regain_right = regain // 2
        regain_left = regain // 2
        if regain_right + regain_left < regain:
            regain_right += 1

        if regain_right > crop_right:
            diff = regain_right - crop_right
            regain_right = crop_right
            regain_left += diff
        elif regain_left > crop_left:
            diff = regain_left - crop_left
            regain_left = crop_left
            regain_right += diff

        assert regain_right <= crop_right, (
            "Failed to get regain_right<=crop_right for height %d, width %d, "
            "crop_top %d, crop_right %d, crop_bottom %d, crop_left %d,"
            "regain_right %d." % (
                height, width, crop_top, crop_right, crop_bottom, crop_left,
                regain_right))
        assert regain_left <= crop_left, (
            "Failed to get regain_left<=crop_left for height %d, width %d, "
            "crop_top %d, crop_right %d, crop_bottom %d, crop_left %d,"
            "regain_left %d." % (
                height, width, crop_top, crop_right, crop_bottom, crop_left,
                regain_left))

        crop_right = crop_right - regain_right
        crop_left = crop_left - regain_left

    return crop_top, crop_right, crop_bottom, crop_left


def _handle_position_parameter(position):
    if position == "uniform":
        return iap.Uniform(0.0, 1.0), iap.Uniform(0.0, 1.0)
    elif position == "normal":
        return (
            iap.Clip(iap.Normal(loc=0.5, scale=0.35 / 2),
                     minval=0.0, maxval=1.0),
            iap.Clip(iap.Normal(loc=0.5, scale=0.35 / 2),
                     minval=0.0, maxval=1.0)
        )
    elif position == "center":
        return iap.Deterministic(0.5), iap.Deterministic(0.5)
    elif (ia.is_string(position)
          and re.match(r"^(left|center|right)-(top|center|bottom)$", position)):
        mapping = {"top": 0.0, "center": 0.5, "bottom": 1.0, "left": 0.0,
                   "right": 1.0}
        return (
            iap.Deterministic(mapping[position.split("-")[0]]),
            iap.Deterministic(mapping[position.split("-")[1]])
        )
    elif isinstance(position, iap.StochasticParameter):
        return position
    elif isinstance(position, tuple):
        assert len(position) == 2, (
            "Expected tuple with two entries as position parameter. "
            "Got %d entries with types %s.." % (
                len(position), str([type(el) for el in position])))
        for el in position:
            if ia.is_single_number(el) and (el < 0 or el > 1.0):
                raise Exception(
                    "Both position values must be within the value range "
                    "[0.0, 1.0]. Got type %s with value %.8f." % (
                        type(el), el,))
        position = [iap.Deterministic(el)
                    if ia.is_single_number(el)
                    else el for el in position]

        only_sparams = all([isinstance(el, iap.StochasticParameter)
                            for el in position])
        assert only_sparams, (
            "Expected tuple with two entries that are both either "
            "StochasticParameter or float/int. Got types %s." % (
                str([type(el) for el in position])
            ))
        return tuple(position)
    else:
        raise Exception(
            "Expected one of the following as position parameter: string "
            "'uniform', string 'normal', string 'center', a string matching "
            "regex ^(left|center|right)-(top|center|bottom)$, a single "
            "StochasticParameter or a tuple of two entries, both being either "
            "StochasticParameter or floats or int. Got instead type %s with "
            "content '%s'." % (
                type(position),
                (str(position)
                 if len(str(position)) < 20
                 else str(position)[0:20] + "...")
            )
        )


@ia.deprecated(alt_func="Resize",
               comment="Resize has the exactly same interface as Scale.")
def Scale(*args, **kwargs):
    return Resize(*args, **kwargs)


class Resize(meta.Augmenter):
    """Augmenter that resizes images to specified heights and widths.

    dtype support::

        See :func:`imgaug.imgaug.imresize_many_images`.

    Parameters
    ----------
    size : 'keep' or int or float or tuple of int or tuple of float or list of int or list of float or imgaug.parameters.StochasticParameter or dict
        The new size of the images.

            * If this has the string value ``keep``, the original height and
              width values will be kept (image is not resized).
            * If this is an ``int``, this value will always be used as the new
              height and width of the images.
            * If this is a ``float`` ``v``, then per image the image's height
              ``H`` and width ``W`` will be changed to ``H*v`` and ``W*v``.
            * If this is a ``tuple``, it is expected to have two entries
              ``(a, b)``. If at least one of these are ``float`` s, a value
              will be sampled from range ``[a, b]`` and used as the ``float``
              value to resize the image (see above). If both are ``int`` s, a
              value will be sampled from the discrete range ``[a..b]`` and
              used as the integer value to resize the image (see above).
            * If this is a ``list``, a random value from the ``list`` will be
              picked to resize the image. All values in the ``list`` must be
              ``int`` s or ``float`` s (no mixture is possible).
            * If this is a ``StochasticParameter``, then this parameter will
              first be queried once per image. The resulting value will be used
              for both height and width.
            * If this is a ``dict``, it may contain the keys ``height`` and
              ``width`` or the keys ``shorter-side`` and ``longer-side``. Each
              key may have the same datatypes as above and describes the
              scaling on x and y-axis or the shorter and longer axis,
              respectively. Both axis are sampled independently. Additionally,
              one of the keys may have the value ``keep-aspect-ratio``, which
              means that the respective side of the image will be resized so
              that the original aspect ratio is kept. This is useful when only
              resizing one image size by a pixel value (e.g. resize images to
              a height of ``64`` pixels and resize the width so that the
              overall aspect ratio is maintained).

    interpolation : imgaug.ALL or int or str or list of int or list of str or imgaug.parameters.StochasticParameter, optional
        Interpolation to use.

            * If ``imgaug.ALL``, then a random interpolation from ``nearest``,
              ``linear``, ``area`` or ``cubic`` will be picked (per image).
            * If ``int``, then this interpolation will always be used.
              Expected to be any of the following:
              ``cv2.INTER_NEAREST``, ``cv2.INTER_LINEAR``, ``cv2.INTER_AREA``,
              ``cv2.INTER_CUBIC``
            * If string, then this interpolation will always be used.
              Expected to be any of the following:
              ``nearest``, ``linear``, ``area``, ``cubic``
            * If ``list`` of ``int`` / ``str``, then a random one of the values
              will be picked per image as the interpolation.
            * If a ``StochasticParameter``, then this parameter will be
              queried per image and is expected to return an ``int`` or
              ``str``.

    name : None or str, optional
        See :func:`imgaug.augmenters.meta.Augmenter.__init__`.

    deterministic : bool, optional
        See :func:`imgaug.augmenters.meta.Augmenter.__init__`.

    random_state : None or int or imgaug.random.RNG or numpy.random.Generator or numpy.random.bit_generator.BitGenerator or numpy.random.SeedSequence or numpy.random.RandomState, optional
        See :func:`imgaug.augmenters.meta.Augmenter.__init__`.

    Examples
    --------
    >>> import imgaug.augmenters as iaa
    >>> aug = iaa.Resize(32)

    Resize all images to ``32x32`` pixels.

    >>> aug = iaa.Resize(0.5)

    Resize all images to ``50`` percent of their original size.

    >>> aug = iaa.Resize((16, 22))

    Resize all images to a random height and width within the discrete
    interval ``[16..22]`` (uniformly sampled per image).

    >>> aug = iaa.Resize((0.5, 0.75))

    Resize all any input image so that its height (``H``) and width (``W``)
    become ``H*v`` and ``W*v``, where ``v`` is uniformly sampled from the
    interval ``[0.5, 0.75]``.

    >>> aug = iaa.Resize([16, 32, 64])

    Resize all images either to ``16x16``, ``32x32`` or ``64x64`` pixels.

    >>> aug = iaa.Resize({"height": 32})

    Resize all images to a height of ``32`` pixels and keeps the original
    width.

    >>> aug = iaa.Resize({"height": 32, "width": 48})

    Resize all images to a height of ``32`` pixels and a width of ``48``.

    >>> aug = iaa.Resize({"height": 32, "width": "keep-aspect-ratio"})

    Resize all images to a height of ``32`` pixels and resizes the
    x-axis (width) so that the aspect ratio is maintained.

    >>> aug = iaa.Resize(
    >>>     {"shorter-side": 224, "longer-side": "keep-aspect-ratio"})

    Resize all images to a height/width of ``224`` pixels, depending on which
    axis is shorter and resize the other axis so that the aspect ratio is
    maintained.

    >>> aug = iaa.Resize({"height": (0.5, 0.75), "width": [16, 32, 64]})

    Resize all images to a height of ``H*v``, where ``H`` is the original
    height and ``v`` is a random value sampled from the interval
    ``[0.5, 0.75]``. The width/x-axis of each image is resized to either
    ``16`` or ``32`` or ``64`` pixels.

    >>> aug = iaa.Resize(32, interpolation=["linear", "cubic"])

    Resize all images to ``32x32`` pixels. Randomly use either ``linear``
    or ``cubic`` interpolation.

    """

    def __init__(self, size, interpolation="cubic",
                 name=None, deterministic=False, random_state=None):
        super(Resize, self).__init__(name=name, deterministic=deterministic,
                                     random_state=random_state)

        def handle(val, allow_dict):
            if val == "keep":
                return iap.Deterministic("keep")
            elif ia.is_single_integer(val):
                assert val > 0, "Expected only values > 0, got %d" % (val,)
                return iap.Deterministic(val)
            elif ia.is_single_float(val):
                assert val > 0, "Expected only values > 0, got %.4f" % (val,)
                return iap.Deterministic(val)
            elif allow_dict and isinstance(val, dict):
                if len(val.keys()) == 0:
                    return iap.Deterministic("keep")
                elif any([key in ["height", "width"] for key in val.keys()]):
                    hw_keys_exist = all([
                        key in ["height", "width"] for key in val.keys()])
                    assert hw_keys_exist, (
                        "Expected dict to contain height and width keys, "
                        "found neither of them.")
                    if "height" in val and "width" in val:
                        not_both_kaa = (
                            val["height"] != "keep-aspect-ratio"
                            or val["width"] != "keep-aspect-ratio")
                        assert not_both_kaa, (
                            "Expected height and width to not be both set "
                            "to \"keep-aspect-ratio\".")

                    size_tuple = []
                    for k in ["height", "width"]:
                        if k in val:
                            if (val[k] == "keep-aspect-ratio"
                                    or val[k] == "keep"):
                                entry = iap.Deterministic(val[k])
                            else:
                                entry = handle(val[k], False)
                        else:
                            entry = iap.Deterministic("keep")
                        size_tuple.append(entry)
                    return tuple(size_tuple)
                elif any([key in ["shorter-side", "longer-side"]
                          for key in val.keys()]):
                    sl_keys_exist = all([
                        key in ["shorter-side", "longer-side"]
                        for key in val.keys()])
                    assert sl_keys_exist, (
                        "Expected dict to contain shorter-side and "
                        "longer-side keys, found neither of them.")
                    if "shorter-side" in val and "longer-side" in val:
                        not_both_kaa = (
                            val["shorter-side"] != "keep-aspect-ratio"
                            or val["longer-side"] != "keep-aspect-ratio")
                        assert not_both_kaa, (
                            "Expected shorter-side and longer-side to not be "
                            "both set to \"keep-aspect-ratio\".")

                    size_tuple = []
                    for k in ["shorter-side", "longer-side"]:
                        if k in val:
                            if (val[k] == "keep-aspect-ratio"
                                    or val[k] == "keep"):
                                entry = iap.Deterministic(val[k])
                            else:
                                entry = handle(val[k], False)
                        else:
                            entry = iap.Deterministic("keep")
                        size_tuple.append(entry)
                    return tuple(size_tuple)

            elif isinstance(val, tuple):
                assert len(val) == 2, (
                    "Expected size tuple to contain exactly 2 values, "
                    "got %d." % (len(val),))
                assert val[0] > 0 and val[1] > 0, (
                    "Expected size tuple to only contain values >0, "
                    "got %d and %d." % (val[0], val[1]))
                if ia.is_single_float(val[0]) or ia.is_single_float(val[1]):
                    return iap.Uniform(val[0], val[1])
                else:
                    return iap.DiscreteUniform(val[0], val[1])
            elif isinstance(val, list):
                if len(val) == 0:
                    return iap.Deterministic("keep")
                else:
                    all_int = all([ia.is_single_integer(v) for v in val])
                    all_float = all([ia.is_single_float(v) for v in val])
                    assert all_int or all_float, (
                        "Expected to get only integers or floats.")
                    assert all([v > 0 for v in val]), (
                        "Expected all values to be >0.")
                    return iap.Choice(val)
            elif isinstance(val, iap.StochasticParameter):
                return val

            raise Exception(
                "Expected number, tuple of two numbers, list of numbers, "
                "dictionary of form "
                "{'height': number/tuple/list/'keep-aspect-ratio'/'keep', "
                "'width': <analogous>}, dictionary of form "
                "{'shorter-side': number/tuple/list/'keep-aspect-ratio'/"
                "'keep', 'longer-side': <analogous>} "
                " or StochasticParameter, got %s." % (type(val),)
            )

        self.size = handle(size, True)
        self.size_order = (
            'SL'
            if (isinstance(size, dict) and 'shorter-side' in size)
            else 'HW')

        if interpolation == ia.ALL:
            self.interpolation = iap.Choice(
                ["nearest", "linear", "area", "cubic"])
        elif ia.is_single_integer(interpolation):
            self.interpolation = iap.Deterministic(interpolation)
        elif ia.is_string(interpolation):
            self.interpolation = iap.Deterministic(interpolation)
        elif ia.is_iterable(interpolation):
            self.interpolation = iap.Choice(interpolation)
        elif isinstance(interpolation, iap.StochasticParameter):
            self.interpolation = interpolation
        else:
            raise Exception(
                "Expected int or string or iterable or StochasticParameter, "
                "got %s." % (type(interpolation),))

    def _augment_images(self, images, random_state, parents, hooks):
        result = []
        nb_images = len(images)
        samples_a, samples_b, samples_ip = self._draw_samples(
            nb_images, random_state, do_sample_ip=True)
        for i in sm.xrange(nb_images):
            image = images[i]
            sample_a, sample_b, sample_ip = (samples_a[i], samples_b[i],
                                             samples_ip[i])
            h, w = self._compute_height_width(image.shape, sample_a, sample_b,
                                              self.size_order)
            image_rs = ia.imresize_single_image(image, (h, w),
                                                interpolation=sample_ip)
            result.append(image_rs)

        if not isinstance(images, list):
            all_same_size = (len(set([image.shape for image in result])) == 1)
            if all_same_size:
                result = np.array(result, dtype=np.uint8)

        return result

    def _augment_heatmaps(self, heatmaps, random_state, parents, hooks):
        result = []
        nb_heatmaps = len(heatmaps)
        samples_a, samples_b, samples_ip = self._draw_samples(
            nb_heatmaps, random_state, do_sample_ip=True)

        for i in sm.xrange(nb_heatmaps):
            heatmaps_i = heatmaps[i]
            arr_shape = heatmaps_i.arr_0to1.shape
            img_shape = heatmaps_i.shape
            sample_a, sample_b, sample_ip = \
                samples_a[i], samples_b[i], samples_ip[i]
            h_img, w_img = self._compute_height_width(
                img_shape, sample_a, sample_b, self.size_order)
            h = int(np.round(h_img * (arr_shape[0] / img_shape[0])))
            w = int(np.round(w_img * (arr_shape[1] / img_shape[1])))
            h = max(h, 1)
            w = max(w, 1)
            # TODO change this to always have cubic or automatic interpolation?
            heatmaps_i_resized = heatmaps_i.resize(
                (h, w), interpolation=sample_ip)
            heatmaps_i_resized.shape = (h_img, w_img) + img_shape[2:]
            result.append(heatmaps_i_resized)

        return result

    def _augment_segmentation_maps(self, segmaps, random_state, parents, hooks):
        result = []
        nb_segmaps = len(segmaps)
        samples_h, samples_w, _ = self._draw_samples(
            nb_segmaps, random_state, do_sample_ip=False)
        for i in sm.xrange(nb_segmaps):
            segmaps_i = segmaps[i]
            arr_shape = segmaps_i.arr.shape
            img_shape = segmaps_i.shape
            sample_h, sample_w = samples_h[i], samples_w[i]
            h_img, w_img = self._compute_height_width(
                img_shape, sample_h, sample_w, self.size_order)
            h = int(np.round(h_img * (arr_shape[0] / img_shape[0])))
            w = int(np.round(w_img * (arr_shape[1] / img_shape[1])))
            h = max(h, 1)
            w = max(w, 1)
            heatmaps_i_resized = segmaps_i.resize((h, w))
            heatmaps_i_resized.shape = (h_img, w_img) + img_shape[2:]
            result.append(heatmaps_i_resized)

        return result

    def _augment_keypoints(self, keypoints_on_images, random_state, parents,
                           hooks):
        result = []
        nb_images = len(keypoints_on_images)
        samples_a, samples_b, _samples_ip = self._draw_samples(
            nb_images, random_state, do_sample_ip=False)
        for i in sm.xrange(nb_images):
            keypoints_on_image = keypoints_on_images[i]
            sample_a, sample_b = samples_a[i], samples_b[i]
            h, w = self._compute_height_width(
                keypoints_on_image.shape, sample_a, sample_b, self.size_order)
            new_shape = (h, w) + keypoints_on_image.shape[2:]
            keypoints_on_image_rs = keypoints_on_image.on(new_shape)

            result.append(keypoints_on_image_rs)

        return result

    def _augment_polygons(self, polygons_on_images, random_state, parents,
                          hooks):
        return self._augment_polygons_as_keypoints(
            polygons_on_images, random_state, parents, hooks)

    def _draw_samples(self, nb_images, random_state, do_sample_ip=True):
        rngs = random_state.duplicate(3)
        if isinstance(self.size, tuple):
            samples_h = self.size[0].draw_samples(nb_images,
                                                  random_state=rngs[0])
            samples_w = self.size[1].draw_samples(nb_images,
                                                  random_state=rngs[1])
        else:
            samples_h = self.size.draw_samples(nb_images, random_state=rngs[0])
            samples_w = samples_h
        if do_sample_ip:
            samples_ip = self.interpolation.draw_samples(nb_images,
                                                         random_state=rngs[2])
        else:
            samples_ip = None
        return samples_h, samples_w, samples_ip

    @classmethod
    def _compute_height_width(cls, image_shape, sample_a, sample_b, size_order):
        imh, imw = image_shape[0:2]

        if size_order == 'SL':
            # size order: short, long
            if imh < imw:
                h, w = sample_a, sample_b
            else:
                w, h = sample_a, sample_b

        else:
            # size order: height, width
            h, w = sample_a, sample_b

        if ia.is_single_float(h):
            assert h > 0, "Expected 'h' to be >0, got %.4f" % (h,)
            h = int(np.round(imh * h))
            h = h if h > 0 else 1
        elif h == "keep":
            h = imh
        if ia.is_single_float(w):
            assert w > 0, "Expected 'w' to be >0, got %.4f" % (w,)
            w = int(np.round(imw * w))
            w = w if w > 0 else 1
        elif w == "keep":
            w = imw

        # at least the checks for keep-aspect-ratio must come after
        # the float checks, as they are dependent on the results
        # this is also why these are not written as elifs
        if h == "keep-aspect-ratio":
            h_per_w_orig = imh / imw
            h = int(np.round(w * h_per_w_orig))
        if w == "keep-aspect-ratio":
            w_per_h_orig = imw / imh
            w = int(np.round(h * w_per_h_orig))

        return h, w

    def get_parameters(self):
        return [self.size, self.interpolation, self.size_order]


class CropAndPad(meta.Augmenter):
    """Crop/pad images by pixel amounts or fractions of image sizes.

    Cropping removes pixels at the sides (i.e. extracts a subimage from
    a given full image). Padding adds pixels to the sides (e.g. black pixels).

    This augmenter will never crop images below a height or width of ``1``.

    .. note ::

        This augmenter automatically resizes images back to their original size
        after it has augmented them. To deactivate this, add the
        parameter ``keep_size=False``.

    dtype support::

        if (keep_size=False)::

            * ``uint8``: yes; fully tested
            * ``uint16``: yes; tested
            * ``uint32``: yes; tested
            * ``uint64``: yes; tested
            * ``int8``: yes; tested
            * ``int16``: yes; tested
            * ``int32``: yes; tested
            * ``int64``: yes; tested
            * ``float16``: yes; tested
            * ``float32``: yes; tested
            * ``float64``: yes; tested
            * ``float128``: yes; tested
            * ``bool``: yes; tested

        if (keep_size=True)::

            minimum of (
                ``imgaug.augmenters.size.CropAndPad(keep_size=False)``,
                :func:`imgaug.imgaug.imresize_many_images`
            )

    Parameters
    ----------
    px : None or int or imgaug.parameters.StochasticParameter or tuple, optional
        The number of pixels to crop (negative values) or pad (positive values)
        on each side of the image. Either this or the parameter `percent` may
        be set, not both at the same time.

            * If ``None``, then pixel-based cropping/padding will not be used.
            * If ``int``, then that exact number of pixels will always be
              cropped/padded.
            * If ``StochasticParameter``, then that parameter will be used for
              each image. Four samples will be drawn per image (top, right,
              bottom, left), unless `sample_independently` is set to ``False``,
              as then only one value will be sampled per image and used for
              all sides.
            * If a ``tuple`` of two ``int`` s with values ``a`` and ``b``,
              then each side will be cropped/padded by a random amount sampled
              uniformly per image and side from the inteval ``[a, b]``. If
              however `sample_independently` is set to ``False``, only one
              value will be sampled per image and used for all sides.
            * If a ``tuple`` of four entries, then the entries represent top,
              right, bottom, left. Each entry may be a single ``int`` (always
              crop/pad by exactly that value), a ``tuple`` of two ``int`` s
              ``a`` and ``b`` (crop/pad by an amount within ``[a, b]``), a
              ``list`` of ``int`` s (crop/pad by a random value that is
              contained in the ``list``) or a ``StochasticParameter`` (sample
              the amount to crop/pad from that parameter).

    percent : None or number or imgaug.parameters.StochasticParameter or tuple, optional
        The number of pixels to crop (negative values) or pad (positive values)
        on each side of the image given as a *fraction* of the image
        height/width. E.g. if this is set to ``-0.1``, the augmenter will
        always crop away ``10%`` of the image's height at both the top and the
        bottom (both ``10%`` each), as well as ``10%`` of the width at the
        right and left.
        Expected value range is ``(-1.0, inf)``.
        Either this or the parameter `px` may be set, not both
        at the same time.

            * If ``None``, then fraction-based cropping/padding will not be
              used.
            * If ``number``, then that fraction will always be cropped/padded.
            * If ``StochasticParameter``, then that parameter will be used for
              each image. Four samples will be drawn per image (top, right,
              bottom, left). If however `sample_independently` is set to
              ``False``, only one value will be sampled per image and used for
              all sides.
            * If a ``tuple`` of two ``float`` s with values ``a`` and ``b``,
              then each side will be cropped/padded by a random fraction
              sampled uniformly per image and side from the interval
              ``[a, b]``. If however `sample_independently` is set to
              ``False``, only one value will be sampled per image and used for
              all sides.
            * If a ``tuple`` of four entries, then the entries represent top,
              right, bottom, left. Each entry may be a single ``float``
              (always crop/pad by exactly that percent value), a ``tuple`` of
              two ``float`` s ``a`` and ``b`` (crop/pad by a fraction from
              ``[a, b]``), a ``list`` of ``float`` s (crop/pad by a random
              value that is contained in the list) or a ``StochasticParameter``
              (sample the percentage to crop/pad from that parameter).

    pad_mode : imgaug.ALL or str or list of str or imgaug.parameters.StochasticParameter, optional
        Padding mode to use. The available modes match the numpy padding modes,
        i.e. ``constant``, ``edge``, ``linear_ramp``, ``maximum``, ``median``,
        ``minimum``, ``reflect``, ``symmetric``, ``wrap``. The modes
        ``constant`` and ``linear_ramp`` use extra values, which are provided
        by ``pad_cval`` when necessary. See :func:`imgaug.imgaug.pad` for
        more details.

            * If ``imgaug.ALL``, then a random mode from all available modes
              will be sampled per image.
            * If a ``str``, it will be used as the pad mode for all images.
            * If a ``list`` of ``str``, a random one of these will be sampled
              per image and used as the mode.
            * If ``StochasticParameter``, a random mode will be sampled from
              this parameter per image.

    pad_cval : number or tuple of number list of number or imgaug.parameters.StochasticParameter, optional
        The constant value to use if the pad mode is ``constant`` or the end
        value to use if the mode is ``linear_ramp``.
        See :func:`imgaug.imgaug.pad` for more details.

            * If ``number``, then that value will be used.
            * If a ``tuple`` of two ``number`` s and at least one of them is
              a ``float``, then a random number will be uniformly sampled per
              image from the continuous interval ``[a, b]`` and used as the
              value. If both ``number`` s are ``int`` s, the interval is
              discrete.
            * If a ``list`` of ``number``, then a random value will be chosen
              from the elements of the ``list`` and used as the value.
            * If ``StochasticParameter``, a random value will be sampled from
              that parameter per image.

    keep_size : bool, optional
        After cropping and padding, the result image will usually have a
        different height/width compared to the original input image. If this
        parameter is set to ``True``, then the cropped/padded image will be
        resized to the input image's size, i.e. the augmenter's output shape
        is always identical to the input shape.

    sample_independently : bool, optional
        If ``False`` *and* the values for `px`/`percent` result in exactly
        *one* probability distribution for all image sides, only one single
        value will be sampled from that probability distribution and used for
        all sides. I.e. the crop/pad amount then is the same for all sides.
        If ``True``, four values will be sampled independently, one per side.

    name : None or str, optional
        See :func:`imgaug.augmenters.meta.Augmenter.__init__`.

    deterministic : bool, optional
        See :func:`imgaug.augmenters.meta.Augmenter.__init__`.

    random_state : None or int or imgaug.random.RNG or numpy.random.Generator or numpy.random.bit_generator.BitGenerator or numpy.random.SeedSequence or numpy.random.RandomState, optional
        See :func:`imgaug.augmenters.meta.Augmenter.__init__`.

    Examples
    --------
    >>> import imgaug.augmenters as iaa
    >>> aug = iaa.CropAndPad(px=(-10, 0))

    Crop each side by a random pixel value sampled uniformly per image and
    side from the discrete interval ``[-10..0]``.

    >>> aug = iaa.CropAndPad(px=(0, 10))

    Pad each side by a random pixel value sampled uniformly per image and
    side from the discrete interval ``[0..10]``. The padding happens by
    zero-padding, i.e. it adds black pixels (default setting).

    >>> aug = iaa.CropAndPad(px=(0, 10), pad_mode="edge")

    Pad each side by a random pixel value sampled uniformly per image and
    side from the discrete interval ``[0..10]``. The padding uses the
    ``edge`` mode from numpy's pad function, i.e. the pixel colors around
    the image sides are repeated.

    >>> aug = iaa.CropAndPad(px=(0, 10), pad_mode=["constant", "edge"])

    Similar to the previous example, but uses zero-padding (``constant``) for
    half of the images and ``edge`` padding for the other half.

    >>> aug = iaa.CropAndPad(px=(0, 10), pad_mode=ia.ALL, pad_cval=(0, 255))

    Similar to the previous example, but uses any available padding mode.
    In case the padding mode ends up being ``constant`` or ``linear_ramp``,
    and random intensity is uniformly sampled (once per image) from the
    discrete interval ``[0..255]`` and used as the intensity of the new
    pixels.

    >>> aug = iaa.CropAndPad(px=(0, 10), sample_independently=False)

    Pad each side by a random pixel value sampled uniformly once per image
    from the discrete interval ``[0..10]``. Each sampled value is used
    for *all* sides of the corresponding image.

    >>> aug = iaa.CropAndPad(px=(0, 10), keep_size=False)

    Pad each side by a random pixel value sampled uniformly per image and
    side from the discrete interval ``[0..10]``. Afterwards, do **not**
    resize the padded image back to the input image's size. This will increase
    the image's height and width by a maximum of ``20`` pixels.

    >>> aug = iaa.CropAndPad(px=((0, 10), (0, 5), (0, 10), (0, 5)))

    Pad the top and bottom by a random pixel value sampled uniformly from the
    discrete interval ``[0..10]``. Pad the left and right analogously by
    a random value sampled from ``[0..5]``. Each value is always sampled
    independently.

    >>> aug = iaa.CropAndPad(percent=(0, 0.1))

    Pad each side by a random fraction sampled uniformly from the continuous
    interval ``[0.0, 0.10]``. The fraction is sampled once per image and
    side. E.g. a sampled fraction of ``0.1`` for the top side would pad by
    ``0.1*H``, where ``H`` is the height of the input image.

    >>> aug = iaa.CropAndPad(
    >>>     percent=([0.05, 0.1], [0.05, 0.1], [0.05, 0.1], [0.05, 0.1]))

    Pads each side by either ``5%`` or ``10%``. The values are sampled
    once per side and image.

    >>> aug = iaa.CropAndPad(px=(-10, 10))

    Sample uniformly per image and side a value ``v`` from the discrete range
    ``[-10..10]``. Then either crop (negative sample) or pad (positive sample)
    the side by ``v`` pixels.

    """

    def __init__(self, px=None, percent=None, pad_mode="constant", pad_cval=0,
                 keep_size=True, sample_independently=True,
                 name=None, deterministic=False, random_state=None):
        super(CropAndPad, self).__init__(
            name=name, deterministic=deterministic, random_state=random_state)

        self.all_sides = None
        self.top = None
        self.right = None
        self.bottom = None
        self.left = None
        if px is None and percent is None:
            self.mode = "noop"
        elif px is not None and percent is not None:
            raise Exception("Can only pad by pixels or percent, not both.")
        elif px is not None:
            self.mode = "px"
            if ia.is_single_integer(px):
                self.all_sides = iap.Deterministic(px)
            elif isinstance(px, tuple):
                assert len(px) in [2, 4], (
                    "Expected 'px' given as a tuple to contain 2 or 4 "
                    "entries, got %d." % (len(px),))

                def handle_param(p):
                    if ia.is_single_integer(p):
                        return iap.Deterministic(p)
                    elif isinstance(p, tuple):
                        assert len(p) == 2, (
                            "Expected tuple of 2 values, got %d." % (len(p)))
                        only_ints = (
                            ia.is_single_integer(p[0])
                            and ia.is_single_integer(p[1]))
                        assert only_ints, (
                            "Expected tuple of integers, got %s and %s." % (
                                type(p[0]), type(p[1])))
                        return iap.DiscreteUniform(p[0], p[1])
                    elif isinstance(p, list):
                        assert len(p) > 0, (
                            "Expected non-empty list, but got empty one.")
                        assert all([ia.is_single_integer(val) for val in p]), (
                            "Expected list of ints, got types %s." % (
                                ", ".join([str(type(v)) for v in p])))
                        return iap.Choice(p)
                    elif isinstance(p, iap.StochasticParameter):
                        return p
                    else:
                        raise Exception(
                            "Expected int, tuple of two ints, list of ints or "
                            "StochasticParameter, got type %s." % (type(p),))

                if len(px) == 2:
                    self.all_sides = handle_param(px)
                else:  # len == 4
                    self.top = handle_param(px[0])
                    self.right = handle_param(px[1])
                    self.bottom = handle_param(px[2])
                    self.left = handle_param(px[3])
            elif isinstance(px, iap.StochasticParameter):
                self.top = self.right = self.bottom = self.left = px
            else:
                raise Exception(
                    "Expected int, tuple of 4 "
                    "ints/tuples/lists/StochasticParameters or "
                    "StochasticParameter, got type %s." % (type(px),))
        else:  # = elif percent is not None:
            self.mode = "percent"
            if ia.is_single_number(percent):
                assert percent > -1.0, (
                    "Expected 'percent' to be >-1.0, got %.4f." % (percent,))
                self.all_sides = iap.Deterministic(percent)
            elif isinstance(percent, tuple):
                assert len(percent) in [2, 4], (
                    "Expected 'percent' given as a tuple to contain 2 or 4 "
                    "entries, got %d." % (len(px),))

                def handle_param(p):
                    if ia.is_single_number(p):
                        return iap.Deterministic(p)
                    elif isinstance(p, tuple):
                        assert len(p) == 2, (
                            "Expected tuple of 2 values, got %d." % (len(p)))
                        only_numbers = (
                            ia.is_single_number(p[0])
                            and ia.is_single_number(p[1]))
                        assert only_numbers, (
                            "Expected tuple of numbers, got %s and %s." % (
                                type(p[0]), type(p[1])))
                        assert p[0] > -1.0 and p[1] > -1.0, (
                            "Expected tuple of values >-1.0, got %.4f and "
                            "%.4f." % (p[0], p[1]))
                        return iap.Uniform(p[0], p[1])
                    elif isinstance(p, list):
                        assert len(p) > 0, (
                            "Expected non-empty list, but got empty one.")
                        assert all([ia.is_single_number(val) for val in p]), (
                            "Expected list of numbers, got types %s." % (
                                ", ".join([str(type(v)) for v in p])))
                        assert all([val > -1.0 for val in p]), (
                            "Expected list of values >-1.0, got values %s." % (
                                ", ".join(["%.4f" % (v,) for v in p])))
                        return iap.Choice(p)
                    elif isinstance(p, iap.StochasticParameter):
                        return p
                    else:
                        raise Exception(
                            "Expected int, tuple of two ints, list of ints or "
                            "StochasticParameter, got type %s." % (type(p),))

                if len(percent) == 2:
                    self.all_sides = handle_param(percent)
                else:  # len == 4
                    self.top = handle_param(percent[0])
                    self.right = handle_param(percent[1])
                    self.bottom = handle_param(percent[2])
                    self.left = handle_param(percent[3])
            elif isinstance(percent, iap.StochasticParameter):
                self.top = self.right = self.bottom = self.left = percent
            else:
                raise Exception(
                    "Expected number, tuple of 4 "
                    "numbers/tuples/lists/StochasticParameters or "
                    "StochasticParameter, got type %s." % (type(percent),))

        self.pad_mode = _handle_pad_mode_param(pad_mode)
        # TODO enable ALL here, like in e.g. Affine
        self.pad_cval = iap.handle_discrete_param(
            pad_cval, "pad_cval", value_range=None, tuple_to_uniform=True,
            list_to_choice=True, allow_floats=True)

        self.keep_size = keep_size
        self.sample_independently = sample_independently

    def _augment_images(self, images, random_state, parents, hooks):
        result = []
        nb_images = len(images)
        rngs = random_state.duplicate(nb_images)
        for i in sm.xrange(nb_images):
            height, width = images[i].shape[0:2]
            crop_top, crop_right, crop_bottom, crop_left, \
                pad_top, pad_right, pad_bottom, pad_left, pad_mode, \
                pad_cval = self._draw_samples_image(rngs[i], height, width)

            image_cr = images[i][crop_top:height-crop_bottom,
                                 crop_left:width-crop_right,
                                 :]

            image_cr_pa = ia.pad(
                image_cr, top=pad_top, right=pad_right, bottom=pad_bottom,
                left=pad_left, mode=pad_mode, cval=pad_cval)

            if self.keep_size:
                image_cr_pa = ia.imresize_single_image(image_cr_pa,
                                                       (height, width))

            result.append(image_cr_pa)

        if ia.is_np_array(images):
            if self.keep_size:
                result = np.array(result, dtype=images.dtype)
            else:
                nb_shapes = len(set([image.shape for image in result]))
                if nb_shapes == 1:
                    result = np.array(result, dtype=images.dtype)

        return result

    def _augment_heatmaps(self, heatmaps, random_state, parents, hooks):
        result = []
        nb_heatmaps = len(heatmaps)
        rngs = random_state.duplicate(nb_heatmaps)
        for i in sm.xrange(nb_heatmaps):
            height_img, width_img = heatmaps[i].shape[0:2]
            height_hms, width_hms = heatmaps[i].arr_0to1.shape[0:2]

            vals = self._draw_samples_image(rngs[i], height_img, width_img)
            crop_img_t, crop_img_r, crop_img_b, crop_img_l, pad_img_t, \
                pad_img_r, pad_img_b, pad_img_l, _pad_mode, _pad_cval = vals

            if (height_img, width_img) != (height_hms, width_hms):
                crop_top = _int_r(height_hms * (crop_img_t/height_img))
                crop_right = _int_r(width_hms * (crop_img_r/width_img))
                crop_bottom = _int_r(height_hms * (crop_img_b/height_img))
                crop_left = _int_r(width_hms * (crop_img_l/width_img))

                crop_top, crop_right, crop_bottom, crop_left = \
                    _crop_prevent_zero_size(
                        height_hms, width_hms,
                        crop_top, crop_right, crop_bottom, crop_left)

                pad_top = _int_r(height_hms * (pad_img_t/height_img))
                pad_right = _int_r(width_hms * (pad_img_r/width_img))
                pad_bottom = _int_r(height_hms * (pad_img_b/height_img))
                pad_left = _int_r(width_hms * (pad_img_l/width_img))
            else:
                crop_top = crop_img_t
                crop_right = crop_img_r
                crop_bottom = crop_img_b
                crop_left = crop_img_l

                pad_top = pad_img_t
                pad_right = pad_img_r
                pad_bottom = pad_img_b
                pad_left = pad_img_l

            arr_cr = heatmaps[i].arr_0to1[crop_top:height_hms-crop_bottom,
                                          crop_left:width_hms-crop_right,
                                          :]

            # TODO switch to ia.pad()
            if any([pad_top > 0, pad_right > 0, pad_bottom > 0, pad_left > 0]):
                if arr_cr.ndim == 2:
                    pad_vals = ((pad_top, pad_bottom), (pad_left, pad_right))
                else:
                    pad_vals = ((pad_top, pad_bottom), (pad_left, pad_right),
                                (0, 0))

                arr_cr_pa = np.pad(arr_cr, pad_vals, mode="constant",
                                   constant_values=0)
            else:
                arr_cr_pa = arr_cr

            heatmaps[i].arr_0to1 = arr_cr_pa

            if self.keep_size:
                heatmaps[i] = heatmaps[i].resize((height_hms, width_hms))
            else:
                new_height = (
                    heatmaps[i].shape[0]
                    - crop_img_t - crop_img_b
                    + pad_img_t + pad_img_b)
                new_width = (
                    heatmaps[i].shape[1]
                    - crop_img_l - crop_img_r
                    + pad_img_l + pad_img_r)
                heatmaps[i].shape = (
                    new_height,
                    new_width
                ) + heatmaps[i].shape[2:]

            result.append(heatmaps[i])

        return result

    def _augment_segmentation_maps(self, segmaps, random_state, parents, hooks):
        result = []
        nb_segmaps = len(segmaps)
        rngs = random_state.duplicate(nb_segmaps)
        for i in sm.xrange(nb_segmaps):
            height_img, width_img = segmaps[i].shape[0:2]
            height_seg, width_seg = segmaps[i].arr.shape[0:2]

            vals = self._draw_samples_image(rngs[i], height_img, width_img)
            crop_img_t, crop_img_r, crop_img_b, crop_img_l, pad_img_t,\
                pad_img_r, pad_img_b, pad_img_l, _pad_mode, _pad_cval = vals

            if (height_img, width_img) != (height_seg, width_seg):
                crop_top = _int_r(height_seg * (crop_img_t/height_img))
                crop_right = _int_r(width_seg * (crop_img_r/width_img))
                crop_bottom = _int_r(height_seg * (crop_img_b/height_img))
                crop_left = _int_r(width_seg * (crop_img_l/width_img))

                crop_top, crop_right, crop_bottom, crop_left = \
                    _crop_prevent_zero_size(
                        height_seg, width_seg, crop_top, crop_right,
                        crop_bottom, crop_left)

                pad_top = _int_r(height_seg * (pad_img_t/height_img))
                pad_right = _int_r(width_seg * (pad_img_r/width_img))
                pad_bottom = _int_r(height_seg * (pad_img_b/height_img))
                pad_left = _int_r(width_seg * (pad_img_l/width_img))
            else:
                crop_top = crop_img_t
                crop_right = crop_img_r
                crop_bottom = crop_img_b
                crop_left = crop_img_l

                pad_top = pad_img_t
                pad_right = pad_img_r
                pad_bottom = pad_img_b
                pad_left = pad_img_l

            arr_cr = segmaps[i].arr[crop_top:height_seg - crop_bottom,
                                    crop_left:width_seg - crop_right,
                                    :]

            # TODO switch to ia.pad()
            if any([pad_top > 0, pad_right > 0, pad_bottom > 0, pad_left > 0]):
                if arr_cr.ndim == 2:
                    pad_vals = ((pad_top, pad_bottom), (pad_left, pad_right))
                else:
                    pad_vals = ((pad_top, pad_bottom), (pad_left, pad_right),
                                (0, 0))

                arr_cr_pa = np.pad(arr_cr, pad_vals, mode="constant",
                                   constant_values=0)
            else:
                arr_cr_pa = arr_cr

            segmaps[i].arr = arr_cr_pa

            if self.keep_size:
                segmaps[i] = segmaps[i].resize((height_seg, width_seg))
            else:
                new_height = (
                    segmaps[i].shape[0]
                    - crop_img_t - crop_img_b
                    + pad_img_t + pad_img_b)
                new_width = (
                    segmaps[i].shape[1]
                    - crop_img_l - crop_img_r
                    + pad_img_l + pad_img_r)
                segmaps[i].shape = (
                   new_height,
                   new_width
                ) + segmaps[i].shape[2:]

            result.append(segmaps[i])

        return result

    def _augment_keypoints(self, keypoints_on_images, random_state, parents,
                           hooks):
        result = []
        nb_images = len(keypoints_on_images)
        rngs = random_state.duplicate(nb_images)
        for i, keypoints_on_image in enumerate(keypoints_on_images):
            height, width = keypoints_on_image.shape[0:2]
            crop_top, crop_right, crop_bottom, crop_left, \
                pad_top, pad_right, pad_bottom, pad_left, _pad_mode, \
                _pad_cval = self._draw_samples_image(rngs[i], height, width)
            shifted = keypoints_on_image.shift(
                x=-crop_left+pad_left, y=-crop_top+pad_top)
            shifted.shape = (
                height - crop_top - crop_bottom + pad_top + pad_bottom,
                width - crop_left - crop_right + pad_left + pad_right
            ) + shifted.shape[2:]
            if self.keep_size:
                result.append(shifted.on(keypoints_on_image.shape))
            else:
                result.append(shifted)

        return result

    def _augment_polygons(self, polygons_on_images, random_state, parents,
                          hooks):
        return self._augment_polygons_as_keypoints(
            polygons_on_images, random_state, parents, hooks)

    def _draw_samples_image(self, random_state, height, width):
        if self.mode == "noop":
            top = right = bottom = left = 0
        else:
            if self.all_sides is not None:
                if self.sample_independently:
                    samples = self.all_sides.draw_samples(
                        (4,), random_state=random_state)
                    top, right, bottom, left = samples
                else:
                    sample = self.all_sides.draw_sample(
                        random_state=random_state)
                    top = right = bottom = left = sample
            else:
                top = self.top.draw_sample(random_state=random_state)
                right = self.right.draw_sample(random_state=random_state)
                bottom = self.bottom.draw_sample(random_state=random_state)
                left = self.left.draw_sample(random_state=random_state)

            if self.mode == "px":
                # no change necessary for pixel values
                pass
            elif self.mode == "percent":
                # percentage values have to be transformed to pixel values
                top = int(np.round(height * top))
                right = int(np.round(width * right))
                bottom = int(np.round(height * bottom))
                left = int(np.round(width * left))
            else:
                raise Exception("Invalid mode")

        crop_top = (-1) * top if top < 0 else 0
        crop_right = (-1) * right if right < 0 else 0
        crop_bottom = (-1) * bottom if bottom < 0 else 0
        crop_left = (-1) * left if left < 0 else 0

        pad_top = top if top > 0 else 0
        pad_right = right if right > 0 else 0
        pad_bottom = bottom if bottom > 0 else 0
        pad_left = left if left > 0 else 0

        pad_mode = self.pad_mode.draw_sample(random_state=random_state)
        pad_cval = self.pad_cval.draw_sample(random_state=random_state)
        pad_cval = np.clip(np.round(pad_cval), 0, 255).astype(np.uint8)

        crop_top, crop_right, crop_bottom, crop_left = _crop_prevent_zero_size(
            height, width, crop_top, crop_right, crop_bottom, crop_left)

        assert (
            crop_top >= 0
            and crop_right >= 0
            and crop_bottom >= 0
            and crop_left >= 0), (
            "Expected to generate only crop amounts >=0, "
            "got %d, %d, %d, %d (top, right, botto, left)." % (
                crop_top, crop_right, crop_bottom, crop_left))
        assert crop_top + crop_bottom < height, (
            "Expected generated crop amounts at top/bottom to not exceed "
            "image height, got %d and %d vs. image height %d." % (
                crop_top, crop_bottom, height))
        assert crop_right + crop_left < width, (
            "Expected generated crop amounts at left/right to not exceed "
            "image width, got %d and %d vs. image width %d." % (
                crop_left, crop_right, width))

        return (crop_top, crop_right, crop_bottom, crop_left,
                pad_top, pad_right, pad_bottom, pad_left,
                pad_mode, pad_cval)

    def get_parameters(self):
        return [self.all_sides, self.top, self.right, self.bottom, self.left,
                self.pad_mode, self.pad_cval]


class Pad(CropAndPad):
    """Pad images, i.e. adds columns/rows of pixels to them.

    dtype support::

        See ``imgaug.augmenters.size.CropAndPad``.

    Parameters
    ----------
    px : None or int or imgaug.parameters.StochasticParameter or tuple, optional
        The number of pixels to pad on each side of the image.
        Expected value range is ``[0, inf)``.
        Either this or the parameter `percent` may be set, not both at the same
        time.

            * If ``None``, then pixel-based padding will not be used.
            * If ``int``, then that exact number of pixels will always be
              padded.
            * If ``StochasticParameter``, then that parameter will be used for
              each image. Four samples will be drawn per image (top, right,
              bottom, left), unless `sample_independently` is set to ``False``,
              as then only one value will be sampled per image and used for
              all sides.
            * If a ``tuple`` of two ``int`` s with values ``a`` and ``b``,
              then each side will be padded by a random amount sampled
              uniformly per image and side from the inteval ``[a, b]``. If
              however `sample_independently` is set to ``False``, only one
              value will be sampled per image and used for all sides.
            * If a ``tuple`` of four entries, then the entries represent top,
              right, bottom, left. Each entry may be a single ``int`` (always
              pad by exactly that value), a ``tuple`` of two ``int`` s
              ``a`` and ``b`` (pad by an amount within ``[a, b]``), a
              ``list`` of ``int`` s (pad by a random value that is
              contained in the ``list``) or a ``StochasticParameter`` (sample
              the amount to pad from that parameter).

    percent : None or int or float or imgaug.parameters.StochasticParameter or tuple, optional
        The number of pixels to pad
        on each side of the image given as a *fraction* of the image
        height/width. E.g. if this is set to ``0.1``, the augmenter will
        always pad ``10%`` of the image's height at both the top and the
        bottom (both ``10%`` each), as well as ``10%`` of the width at the
        right and left.
        Expected value range is ``[0.0, inf)``.
        Either this or the parameter `px` may be set, not both
        at the same time.

            * If ``None``, then fraction-based padding will not be
              used.
            * If ``number``, then that fraction will always be padded.
            * If ``StochasticParameter``, then that parameter will be used for
              each image. Four samples will be drawn per image (top, right,
              bottom, left). If however `sample_independently` is set to
              ``False``, only one value will be sampled per image and used for
              all sides.
            * If a ``tuple`` of two ``float`` s with values ``a`` and ``b``,
              then each side will be padded by a random fraction
              sampled uniformly per image and side from the interval
              ``[a, b]``. If however `sample_independently` is set to
              ``False``, only one value will be sampled per image and used for
              all sides.
            * If a ``tuple`` of four entries, then the entries represent top,
              right, bottom, left. Each entry may be a single ``float``
              (always pad by exactly that fraction), a ``tuple`` of
              two ``float`` s ``a`` and ``b`` (pad by a fraction from
              ``[a, b]``), a ``list`` of ``float`` s (pad by a random
              value that is contained in the list) or a ``StochasticParameter``
              (sample the percentage to pad from that parameter).

    pad_mode : imgaug.ALL or str or list of str or imgaug.parameters.StochasticParameter, optional
        Padding mode to use. The available modes match the numpy padding modes,
        i.e. ``constant``, ``edge``, ``linear_ramp``, ``maximum``, ``median``,
        ``minimum``, ``reflect``, ``symmetric``, ``wrap``. The modes
        ``constant`` and ``linear_ramp`` use extra values, which are provided
        by ``pad_cval`` when necessary. See :func:`imgaug.imgaug.pad` for
        more details.

            * If ``imgaug.ALL``, then a random mode from all available modes
              will be sampled per image.
            * If a ``str``, it will be used as the pad mode for all images.
            * If a ``list`` of ``str``, a random one of these will be sampled
              per image and used as the mode.
            * If ``StochasticParameter``, a random mode will be sampled from
              this parameter per image.

    pad_cval : number or tuple of number list of number or imgaug.parameters.StochasticParameter, optional
        The constant value to use if the pad mode is ``constant`` or the end
        value to use if the mode is ``linear_ramp``.
        See :func:`imgaug.imgaug.pad` for more details.

            * If ``number``, then that value will be used.
            * If a ``tuple`` of two ``number`` s and at least one of them is
              a ``float``, then a random number will be uniformly sampled per
              image from the continuous interval ``[a, b]`` and used as the
              value. If both ``number`` s are ``int`` s, the interval is
              discrete.
            * If a ``list`` of ``number``, then a random value will be chosen
              from the elements of the ``list`` and used as the value.
            * If ``StochasticParameter``, a random value will be sampled from
              that parameter per image.

    keep_size : bool, optional
        After padding, the result image will usually have a
        different height/width compared to the original input image. If this
        parameter is set to ``True``, then the padded image will be
        resized to the input image's size, i.e. the augmenter's output shape
        is always identical to the input shape.

    sample_independently : bool, optional
        If ``False`` *and* the values for `px`/`percent` result in exactly
        *one* probability distribution for all image sides, only one single
        value will be sampled from that probability distribution and used for
        all sides. I.e. the pad amount then is the same for all sides.
        If ``True``, four values will be sampled independently, one per side.

    name : None or str, optional
        See :func:`imgaug.augmenters.meta.Augmenter.__init__`.

    deterministic : bool, optional
        See :func:`imgaug.augmenters.meta.Augmenter.__init__`.

    random_state : None or int or imgaug.random.RNG or numpy.random.Generator or numpy.random.bit_generator.BitGenerator or numpy.random.SeedSequence or numpy.random.RandomState, optional
        See :func:`imgaug.augmenters.meta.Augmenter.__init__`.

    Examples
    --------
    >>> import imgaug.augmenters as iaa
    >>> aug = iaa.Pad(px=(0, 10))

    Pad each side by a random pixel value sampled uniformly per image and
    side from the discrete interval ``[0..10]``. The padding happens by
    zero-padding, i.e. it adds black pixels (default setting).

    >>> aug = iaa.Pad(px=(0, 10), pad_mode="edge")

    Pad each side by a random pixel value sampled uniformly per image and
    side from the discrete interval ``[0..10]``. The padding uses the
    ``edge`` mode from numpy's pad function, i.e. the pixel colors around
    the image sides are repeated.

    >>> aug = iaa.Pad(px=(0, 10), pad_mode=["constant", "edge"])

    Similar to the previous example, but uses zero-padding (``constant``) for
    half of the images and ``edge`` padding for the other half.

    >>> aug = iaa.Pad(px=(0, 10), pad_mode=ia.ALL, pad_cval=(0, 255))

    Similar to the previous example, but uses any available padding mode.
    In case the padding mode ends up being ``constant`` or ``linear_ramp``,
    and random intensity is uniformly sampled (once per image) from the
    discrete interval ``[0..255]`` and used as the intensity of the new
    pixels.

    >>> aug = iaa.Pad(px=(0, 10), sample_independently=False)

    Pad each side by a random pixel value sampled uniformly once per image
    from the discrete interval ``[0..10]``. Each sampled value is used
    for *all* sides of the corresponding image.

    >>> aug = iaa.Pad(px=(0, 10), keep_size=False)

    Pad each side by a random pixel value sampled uniformly per image and
    side from the discrete interval ``[0..10]``. Afterwards, do **not**
    resize the padded image back to the input image's size. This will increase
    the image's height and width by a maximum of ``20`` pixels.

    >>> aug = iaa.Pad(px=((0, 10), (0, 5), (0, 10), (0, 5)))

    Pad the top and bottom by a random pixel value sampled uniformly from the
    discrete interval ``[0..10]``. Pad the left and right analogously by
    a random value sampled from ``[0..5]``. Each value is always sampled
    independently.

    >>> aug = iaa.Pad(percent=(0, 0.1))

    Pad each side by a random fraction sampled uniformly from the continuous
    interval ``[0.0, 0.10]``. The fraction is sampled once per image and
    side. E.g. a sampled fraction of ``0.1`` for the top side would pad by
    ``0.1*H``, where ``H`` is the height of the input image.

    >>> aug = iaa.Pad(
    >>>     percent=([0.05, 0.1], [0.05, 0.1], [0.05, 0.1], [0.05, 0.1]))

    Pads each side by either ``5%`` or ``10%``. The values are sampled
    once per side and image.

    """

    def __init__(self, px=None, percent=None, pad_mode="constant", pad_cval=0,
                 keep_size=True, sample_independently=True,
                 name=None, deterministic=False, random_state=None):
        def recursive_validate(v):
            if v is None:
                return v
            elif ia.is_single_number(v):
                assert v >= 0, "Expected value >0, got %.4f" % (v,)
                return v
            elif isinstance(v, iap.StochasticParameter):
                return v
            elif isinstance(v, tuple):
                return tuple([recursive_validate(v_) for v_ in v])
            elif isinstance(v, list):
                return [recursive_validate(v_) for v_ in v]
            else:
                raise Exception(
                    "Expected None or int or float or StochasticParameter or "
                    "list or tuple, got %s." % (type(v),))

        px = recursive_validate(px)
        percent = recursive_validate(percent)

        super(Pad, self).__init__(
            px=px,
            percent=percent,
            pad_mode=pad_mode,
            pad_cval=pad_cval,
            keep_size=keep_size,
            sample_independently=sample_independently,
            name=name,
            deterministic=deterministic,
            random_state=random_state
        )


class Crop(CropAndPad):
    """Crop images, i.e. remove columns/rows of pixels at the sides of images.

    This augmenter allows to extract smaller-sized subimages from given
    full-sized input images. The number of pixels to cut off may be defined
    in absolute values or as fractions of the image sizes.

    This augmenter will never crop images below a height or width of ``1``.

    dtype support::

        See ``imgaug.augmenters.size.CropAndPad``.

    Parameters
    ----------
    px : None or int or imgaug.parameters.StochasticParameter or tuple, optional
        The number of pixels to crop on each side of the image.
        Expected value range is ``[0, inf)``.
        Either this or the parameter `percent` may be set, not both at the same
        time.

            * If ``None``, then pixel-based cropping will not be used.
            * If ``int``, then that exact number of pixels will always be
              cropped.
            * If ``StochasticParameter``, then that parameter will be used for
              each image. Four samples will be drawn per image (top, right,
              bottom, left), unless `sample_independently` is set to ``False``,
              as then only one value will be sampled per image and used for
              all sides.
            * If a ``tuple`` of two ``int`` s with values ``a`` and ``b``,
              then each side will be cropped by a random amount sampled
              uniformly per image and side from the inteval ``[a, b]``. If
              however `sample_independently` is set to ``False``, only one
              value will be sampled per image and used for all sides.
            * If a ``tuple`` of four entries, then the entries represent top,
              right, bottom, left. Each entry may be a single ``int`` (always
              crop by exactly that value), a ``tuple`` of two ``int`` s
              ``a`` and ``b`` (crop by an amount within ``[a, b]``), a
              ``list`` of ``int`` s (crop by a random value that is
              contained in the ``list``) or a ``StochasticParameter`` (sample
              the amount to crop from that parameter).

    percent : None or int or float or imgaug.parameters.StochasticParameter or tuple, optional
        The number of pixels to crop
        on each side of the image given as a *fraction* of the image
        height/width. E.g. if this is set to ``0.1``, the augmenter will
        always crop ``10%`` of the image's height at both the top and the
        bottom (both ``10%`` each), as well as ``10%`` of the width at the
        right and left.
        Expected value range is ``[0.0, 1.0)``.
        Either this or the parameter `px` may be set, not both
        at the same time.

            * If ``None``, then fraction-based cropping will not be
              used.
            * If ``number``, then that fraction will always be cropped.
            * If ``StochasticParameter``, then that parameter will be used for
              each image. Four samples will be drawn per image (top, right,
              bottom, left). If however `sample_independently` is set to
              ``False``, only one value will be sampled per image and used for
              all sides.
            * If a ``tuple`` of two ``float`` s with values ``a`` and ``b``,
              then each side will be cropped by a random fraction
              sampled uniformly per image and side from the interval
              ``[a, b]``. If however `sample_independently` is set to
              ``False``, only one value will be sampled per image and used for
              all sides.
            * If a ``tuple`` of four entries, then the entries represent top,
              right, bottom, left. Each entry may be a single ``float``
              (always crop by exactly that fraction), a ``tuple`` of
              two ``float`` s ``a`` and ``b`` (crop by a fraction from
              ``[a, b]``), a ``list`` of ``float`` s (crop by a random
              value that is contained in the list) or a ``StochasticParameter``
              (sample the percentage to crop from that parameter).

    keep_size : bool, optional
        After cropping, the result image will usually have a
        different height/width compared to the original input image. If this
        parameter is set to ``True``, then the cropped image will be
        resized to the input image's size, i.e. the augmenter's output shape
        is always identical to the input shape.

    sample_independently : bool, optional
        If ``False`` *and* the values for `px`/`percent` result in exactly
        *one* probability distribution for all image sides, only one single
        value will be sampled from that probability distribution and used for
        all sides. I.e. the crop amount then is the same for all sides.
        If ``True``, four values will be sampled independently, one per side.

    name : None or str, optional
        See :func:`imgaug.augmenters.meta.Augmenter.__init__`.

    deterministic : bool, optional
        See :func:`imgaug.augmenters.meta.Augmenter.__init__`.

    random_state : None or int or imgaug.random.RNG or numpy.random.Generator or numpy.random.bit_generator.BitGenerator or numpy.random.SeedSequence or numpy.random.RandomState, optional
        See :func:`imgaug.augmenters.meta.Augmenter.__init__`.

    Examples
    --------
    >>> import imgaug.augmenters as iaa
    >>> aug = iaa.Crop(px=(0, 10))

    Crop each side by a random pixel value sampled uniformly per image and
    side from the discrete interval ``[0..10]``.

    >>> aug = iaa.Crop(px=(0, 10), sample_independently=False)

    Crop each side by a random pixel value sampled uniformly once per image
    from the discrete interval ``[0..10]``. Each sampled value is used
    for *all* sides of the corresponding image.

    >>> aug = iaa.Crop(px=(0, 10), keep_size=False)

    Crop each side by a random pixel value sampled uniformly per image and
    side from the discrete interval ``[0..10]``. Afterwards, do **not**
    resize the cropped image back to the input image's size. This will decrease
    the image's height and width by a maximum of ``20`` pixels.

    >>> aug = iaa.Crop(px=((0, 10), (0, 5), (0, 10), (0, 5)))

    Crop the top and bottom by a random pixel value sampled uniformly from the
    discrete interval ``[0..10]``. Crop the left and right analogously by
    a random value sampled from ``[0..5]``. Each value is always sampled
    independently.

    >>> aug = iaa.Crop(percent=(0, 0.1))

    Crop each side by a random fraction sampled uniformly from the continuous
    interval ``[0.0, 0.10]``. The fraction is sampled once per image and
    side. E.g. a sampled fraction of ``0.1`` for the top side would crop by
    ``0.1*H``, where ``H`` is the height of the input image.

    >>> aug = iaa.Crop(
    >>>     percent=([0.05, 0.1], [0.05, 0.1], [0.05, 0.1], [0.05, 0.1]))

    Crops each side by either ``5%`` or ``10%``. The values are sampled
    once per side and image.

    """

    def __init__(self, px=None, percent=None, keep_size=True,
                 sample_independently=True,
                 name=None, deterministic=False, random_state=None):
        def recursive_negate(v):
            if v is None:
                return v
            elif ia.is_single_number(v):
                assert v >= 0, "Expected value >0, got %.4f." % (v,)
                return -v
            elif isinstance(v, iap.StochasticParameter):
                return iap.Multiply(v, -1)
            elif isinstance(v, tuple):
                return tuple([recursive_negate(v_) for v_ in v])
            elif isinstance(v, list):
                return [recursive_negate(v_) for v_ in v]
            else:
                raise Exception(
                    "Expected None or int or float or StochasticParameter or "
                    "list or tuple, got %s." % (type(v),))

        px = recursive_negate(px)
        percent = recursive_negate(percent)

        super(Crop, self).__init__(
            px=px,
            percent=percent,
            keep_size=keep_size,
            sample_independently=sample_independently,
            name=name,
            deterministic=deterministic,
            random_state=random_state
        )


# TODO maybe rename this to PadToMinimumSize?
# TODO this is very similar to CropAndPad, maybe add a way to generate crop
#      values imagewise via a callback in in CropAndPad?
# TODO why is padding mode and cval here called pad_mode, pad_cval but in other
#      cases mode/cval?
class PadToFixedSize(meta.Augmenter):
    """Pad images to a predefined minimum width and/or height.

    If images are already at the minimum width/height or are larger, they will
    not be padded. Note that this also means that images will not be cropped if
    they exceed the required width/height.

    The augmenter randomly decides per image how to distribute the required
    padding amounts over the image axis. E.g. if 2px have to be padded on the
    left or right to reach the required width, the augmenter will sometimes
    add 2px to the left and 0px to the right, sometimes add 2px to the right
    and 0px to the left and sometimes add 1px to both sides. Set `position`
    to ``center`` to prevent that.

    dtype support::

        See :func:`imgaug.imgaug.pad`.

    Parameters
    ----------
    width : int
        Pad images up to this minimum width.

    height : int
        Pad images up to this minimum height.

    pad_mode : imgaug.ALL or str or list of str or imgaug.parameters.StochasticParameter, optional
        See :func:`imgaug.augmenters.size.CropAndPad.__init__`.

    pad_cval : number or tuple of number or list of number or imgaug.parameters.StochasticParameter, optional
        See :func:`imgaug.augmenters.size.CropAndPad.__init__`.

    position : {'uniform', 'normal', 'center', 'left-top', 'left-center', 'left-bottom', 'center-top', 'center-center', 'center-bottom', 'right-top', 'right-center', 'right-bottom'} or tuple of float or StochasticParameter or tuple of StochasticParameter, optional
        Sets the center point of the padding, which determines how the
        required padding amounts are distributed to each side. For a ``tuple``
        ``(a, b)``, both ``a`` and ``b`` are expected to be in range
        ``[0.0, 1.0]`` and describe the fraction of padding applied to the
        left/right (low/high values for ``a``) and the fraction of padding
        applied to the top/bottom (low/high values for ``b``). A padding
        position at ``(0.5, 0.5)`` would be the center of the image and
        distribute the padding equally to all sides. A padding position at
        ``(0.0, 1.0)`` would be the left-bottom and would apply 100% of the
        required padding to the bottom and left sides of the image so that
        the bottom left corner becomes more and more the new image
        center (depending on how much is padded).

            * If string ``uniform`` then the share of padding is randomly and
              uniformly distributed over each side.
              Equivalent to ``(Uniform(0.0, 1.0), Uniform(0.0, 1.0))``.
            * If string ``normal`` then the share of padding is distributed
              based on a normal distribution, leading to a focus on the
              center of the images.
              Equivalent to
              ``(Clip(Normal(0.5, 0.45/2), 0, 1),
              Clip(Normal(0.5, 0.45/2), 0, 1))``.
            * If string ``center`` then center point of the padding is
              identical to the image center.
              Equivalent to ``(0.5, 0.5)``.
            * If a string matching regex
              ``^(left|center|right)-(top|center|bottom)$``, e.g. ``left-top``
              or ``center-bottom`` then sets the center point of the padding
              to the X-Y position matching that description.
            * If a tuple of float, then expected to have exactly two entries
              between ``0.0`` and ``1.0``, which will always be used as the
              combination the position matching (x, y) form.
            * If a ``StochasticParameter``, then that parameter will be queried
              once per call to ``augment_*()`` to get ``Nx2`` center positions
              in ``(x, y)`` form (with ``N`` the number of images).
            * If a ``tuple`` of ``StochasticParameter``, then expected to have
              exactly two entries that will both be queried per call to
              ``augment_*()``, each for ``(N,)`` values, to get the center
              positions. First parameter is used for ``x`` coordinates,
              second for ``y`` coordinates.

    name : None or str, optional
        See :func:`imgaug.augmenters.meta.Augmenter.__init__`.

    deterministic : bool, optional
        See :func:`imgaug.augmenters.meta.Augmenter.__init__`.

    random_state : None or int or imgaug.random.RNG or numpy.random.Generator or numpy.random.bit_generator.BitGenerator or numpy.random.SeedSequence or numpy.random.RandomState, optional
        See :func:`imgaug.augmenters.meta.Augmenter.__init__`.

    Examples
    --------
    >>> import imgaug.augmenters as iaa
    >>> aug = iaa.PadToFixedSize(width=100, height=100)

    For image sides smaller than ``100`` pixels, pad to ``100`` pixels. Do
    nothing for the other edges. The padding is randomly (uniformly)
    distributed over the sides, so that e.g. sometimes most of the required
    padding is applied to the left, sometimes to the right (analogous
    top/bottom).

    >>> aug = iaa.PadToFixedSize(width=100, height=100, position="center")

    For image sides smaller than ``100`` pixels, pad to ``100`` pixels. Do
    nothing for the other image sides. The padding is always equally
    distributed over the left/right and top/bottom sides.

    >>> aug = iaa.PadToFixedSize(width=100, height=100, pad_mode=ia.ALL)

    For image sides smaller than ``100`` pixels, pad to ``100`` pixels and
    use any possible padding mode for that. Do nothing for the other image
    sides. The padding is always equally distributed over the left/right and
    top/bottom sides.

    >>> aug = iaa.Sequential([
    >>>     iaa.PadToFixedSize(width=100, height=100),
    >>>     iaa.CropToFixedSize(width=100, height=100)
    >>> ])

    Pad images smaller than ``100x100`` until they reach ``100x100``.
    Analogously, crop images larger than ``100x100`` until they reach
    ``100x100``. The output images therefore have a fixed size of ``100x100``.

    """

    def __init__(self, width, height, pad_mode="constant", pad_cval=0,
                 position="uniform",
                 name=None, deterministic=False, random_state=None):
        super(PadToFixedSize, self).__init__(
            name=name, deterministic=deterministic, random_state=random_state)
        self.size = width, height

        # Position of where to pad. The further to the top left this is, the
        # larger the share of pixels that will be added to the top and left
        # sides. I.e. set to (Deterministic(0.0), Deterministic(0.0)) to only
        # add at the top and left, (Deterministic(1.0), Deterministic(1.0))
        # to only add at the bottom right. Analogously (0.5, 0.5) pads equally
        # on both axis, (0.0, 1.0) pads left and bottom, (1.0, 0.0) pads right
        # and top.
        self.position = _handle_position_parameter(position)

        self.pad_mode = _handle_pad_mode_param(pad_mode)
        # TODO enable ALL here like in eg Affine
        self.pad_cval = iap.handle_discrete_param(
            pad_cval, "pad_cval", value_range=None, tuple_to_uniform=True,
            list_to_choice=True, allow_floats=True)

    def _augment_images(self, images, random_state, parents, hooks):
        result = []
        nb_images = len(images)
        w, h = self.size
        pad_xs, pad_ys, pad_modes, pad_cvals = self._draw_samples(nb_images,
                                                                  random_state)
        for i in sm.xrange(nb_images):
            image = images[i]
            ih, iw = image.shape[:2]
            pad_x0, pad_x1, pad_y0, pad_y1 = self._calculate_paddings(
                h, w, ih, iw, pad_xs[i], pad_ys[i])
            image = ia.pad(
                image, top=pad_y0, right=pad_x1, bottom=pad_y1, left=pad_x0,
                mode=pad_modes[i], cval=pad_cvals[i]
            )

            result.append(image)

        # TODO result is always a list. Should this be converted to an array
        #      if possible (not guaranteed that all images have same size,
        #      some might have been larger than desired height/width)
        return result

    def _augment_keypoints(self, keypoints_on_images, random_state, parents,
                           hooks):
        result = []
        nb_images = len(keypoints_on_images)
        w, h = self.size
        pad_xs, pad_ys, _, _ = self._draw_samples(nb_images, random_state)
        for i in sm.xrange(nb_images):
            keypoints_on_image = keypoints_on_images[i]
            ih, iw = keypoints_on_image.shape[:2]
            pad_x0, _pad_x1, pad_y0, _pad_y1 = self._calculate_paddings(
                h, w, ih, iw, pad_xs[i], pad_ys[i])
            keypoints_padded = keypoints_on_image.shift(x=pad_x0, y=pad_y0)
            keypoints_padded.shape = (
                max(ih, h),
                max(iw, w)
            ) + keypoints_padded.shape[2:]

            result.append(keypoints_padded)

        return result

    def _augment_heatmaps(self, heatmaps, random_state, parents, hooks):
        nb_images = len(heatmaps)
        w, h = self.size
        pad_xs, pad_ys, _pad_modes, _pad_cvals = self._draw_samples(nb_images,
                                                                    random_state)
        for i in sm.xrange(nb_images):
            height_img, width_img = heatmaps[i].shape[:2]
            pad_img_l, pad_img_r, pad_img_t, pad_img_b = \
                self._calculate_paddings(
                    h, w, height_img, width_img, pad_xs[i], pad_ys[i])
            height_hm, width_hm = heatmaps[i].arr_0to1.shape[0:2]

            # TODO for 30x30 padded to 32x32 with 15x15 heatmaps this results
            #      in paddings of 1 on each side (assuming
            #      position=(0.5, 0.5)) giving 17x17 heatmaps when they should
            #      be 16x16. Error is due to each side getting projected 0.5
            #      padding which is rounded to 1. This doesn't seem right.
            if (height_img, width_img) != (height_hm, width_hm):
                pad_top = _int_r(height_hm * (pad_img_t/height_img))
                pad_right = _int_r(width_hm * (pad_img_r/width_img))
                pad_bottom = _int_r(height_hm * (pad_img_b/height_img))
                pad_left = _int_r(width_hm * (pad_img_l/width_img))
            else:
                pad_top = pad_img_t
                pad_right = pad_img_r
                pad_bottom = pad_img_b
                pad_left = pad_img_l

            heatmaps[i].arr_0to1 = ia.pad(
                heatmaps[i].arr_0to1,
                top=pad_top, right=pad_right, bottom=pad_bottom, left=pad_left,
                mode="constant", cval=0
            )
            heatmaps[i].shape = (
                height_img + pad_img_t + pad_img_b,
                width_img + pad_img_l + pad_img_r
            ) + heatmaps[i].shape[2:]

        return heatmaps

    def _augment_segmentation_maps(self, segmaps, random_state, parents,
                                   hooks):
        nb_images = len(segmaps)
        w, h = self.size
        pad_xs, pad_ys, _pad_modes, _pad_cvals = self._draw_samples(
            nb_images, random_state)

        for i in sm.xrange(nb_images):
            height_img, width_img = segmaps[i].shape[:2]
            pad_img_l, pad_img_r, pad_img_t, pad_img_b = \
                self._calculate_paddings(
                    h, w, height_img, width_img, pad_xs[i], pad_ys[i])
            height_sm, width_sm = segmaps[i].arr.shape[0:2]

            # TODO for 30x30 padded to 32x32 with 15x15 heatmaps this results
            #      in paddings of 1 on each side (assuming
            #      position=(0.5, 0.5)) giving 17x17 heatmaps when they should
            #      be 16x16. Error is due to each side getting projected 0.5
            #      padding which is rounded to 1. This doesn't seem right.
            if (height_img, width_img) != (height_sm, width_sm):
                pad_top = _int_r(height_sm * (pad_img_t/height_img))
                pad_right = _int_r(width_sm * (pad_img_r/width_img))
                pad_bottom = _int_r(height_sm * (pad_img_b/height_img))
                pad_left = _int_r(width_sm * (pad_img_l/width_img))
            else:
                pad_top = pad_img_t
                pad_right = pad_img_r
                pad_bottom = pad_img_b
                pad_left = pad_img_l

            segmaps[i].arr = ia.pad(
                segmaps[i].arr,
                top=pad_top, right=pad_right, bottom=pad_bottom, left=pad_left,
                mode="constant", cval=0
            )
            segmaps[i].shape = (
                height_img + pad_img_t + pad_img_b,
                width_img + pad_img_l + pad_img_r
            ) + segmaps[i].shape[2:]

        return segmaps

    def _augment_polygons(self, polygons_on_images, random_state, parents,
                          hooks):
        return self._augment_polygons_as_keypoints(
            polygons_on_images, random_state, parents, hooks)

    def _draw_samples(self, nb_images, random_state):
        rngs = random_state.duplicate(4)

        if isinstance(self.position, tuple):
            pad_xs = self.position[0].draw_samples(nb_images,
                                                   random_state=rngs[0])
            pad_ys = self.position[1].draw_samples(nb_images,
                                                   random_state=rngs[1])
        else:
            pads = self.position.draw_samples((nb_images, 2),
                                              random_state=rngs[0])
            pad_xs = pads[:, 0]
            pad_ys = pads[:, 1]

        pad_modes = self.pad_mode.draw_samples(nb_images,
                                               random_state=rngs[2])
        pad_cvals = self.pad_cval.draw_samples(nb_images,
                                               random_state=rngs[3])
        pad_cvals = np.clip(np.round(pad_cvals), 0, 255).astype(np.uint8)

        return pad_xs, pad_ys, pad_modes, pad_cvals

    @classmethod
    def _calculate_paddings(cls, h, w, ih, iw, pad_xs_i, pad_ys_i):
        pad_x1, pad_x0, pad_y1, pad_y0 = 0, 0, 0, 0

        if iw < w:
            pad_x1 = int(pad_xs_i * (w - iw))
            pad_x0 = w - iw - pad_x1

        if ih < h:
            pad_y1 = int(pad_ys_i * (h - ih))
            pad_y0 = h - ih - pad_y1

        return pad_x0, pad_x1, pad_y0, pad_y1

    def get_parameters(self):
        return [self.position, self.pad_mode, self.pad_cval]


# TODO maybe rename this to CropToMaximumSize ?
# TODO this is very similar to CropAndPad, maybe add a way to generate crop
#      values imagewise via a callback in in CropAndPad?
# TODO add crop() function in imgaug, similar to pad
class CropToFixedSize(meta.Augmenter):
    """Crop images down to a predefined  maximum width and/or height.

    If images are already at the maximum width/height or are smaller, they
    will not be cropped. Note that this also means that images will not be
    padded if they are below the required width/height.

    The augmenter randomly decides per image how to distribute the required
    cropping amounts over the image axis. E.g. if 2px have to be cropped on
    the left or right to reach the required width, the augmenter will
    sometimes remove 2px from the left and 0px from the right, sometimes
    remove 2px from the right and 0px from the left and sometimes remove 1px
    from both sides. Set `position` to ``center`` to prevent that.

    dtype support::

        * ``uint8``: yes; fully tested
        * ``uint16``: yes; tested
        * ``uint32``: yes; tested
        * ``uint64``: yes; tested
        * ``int8``: yes; tested
        * ``int16``: yes; tested
        * ``int32``: yes; tested
        * ``int64``: yes; tested
        * ``float16``: yes; tested
        * ``float32``: yes; tested
        * ``float64``: yes; tested
        * ``float128``: yes; tested
        * ``bool``: yes; tested

    Parameters
    ----------
    width : int
        Crop images down to this maximum width.

    height : int
        Crop images down to this maximum height.

    position : {'uniform', 'normal', 'center', 'left-top', 'left-center', 'left-bottom', 'center-top', 'center-center', 'center-bottom', 'right-top', 'right-center', 'right-bottom'} or tuple of float or StochasticParameter or tuple of StochasticParameter, optional
         Sets the center point of the cropping, which determines how the
         required cropping amounts are distributed to each side. For a
         ``tuple`` ``(a, b)``, both ``a`` and ``b`` are expected to be in
         range ``[0.0, 1.0]`` and describe the fraction of cropping applied
         to the left/right (low/high values for ``a``) and the fraction
         of cropping applied to the top/bottom (low/high values for ``b``).
         A cropping position at ``(0.5, 0.5)`` would be the center of the
         image and distribute the cropping equally over all sides. A cropping
         position at ``(1.0, 0.0)`` would be the right-top and would apply
         100% of the required cropping to the right and top sides of the image.

            * If string ``uniform`` then the share of cropping is randomly
              and uniformly distributed over each side.
              Equivalent to ``(Uniform(0.0, 1.0), Uniform(0.0, 1.0))``.
            * If string ``normal`` then the share of cropping is distributed
              based on a normal distribution, leading to a focus on the center
              of the images.
              Equivalent to
              ``(Clip(Normal(0.5, 0.45/2), 0, 1),
              Clip(Normal(0.5, 0.45/2), 0, 1))``.
            * If string ``center`` then center point of the cropping is
              identical to the image center.
              Equivalent to ``(0.5, 0.5)``.
            * If a string matching regex
              ``^(left|center|right)-(top|center|bottom)$``, e.g.
              ``left-top`` or ``center-bottom`` then sets the center point of
              the cropping to the X-Y position matching that description.
            * If a tuple of float, then expected to have exactly two entries
              between ``0.0`` and ``1.0``, which will always be used as the
              combination the position matching (x, y) form.
            * If a ``StochasticParameter``, then that parameter will be queried
              once per call to ``augment_*()`` to get ``Nx2`` center positions
              in ``(x, y)`` form (with ``N`` the number of images).
            * If a ``tuple`` of ``StochasticParameter``, then expected to have
              exactly two entries that will both be queried per call to
              ``augment_*()``, each for ``(N,)`` values, to get the center
              positions. First parameter is used for ``x`` coordinates,
              second for ``y`` coordinates.

    name : None or str, optional
        See :func:`imgaug.augmenters.meta.Augmenter.__init__`.

    deterministic : bool, optional
        See :func:`imgaug.augmenters.meta.Augmenter.__init__`.

    random_state : None or int or imgaug.random.RNG or numpy.random.Generator or numpy.random.bit_generator.BitGenerator or numpy.random.SeedSequence or numpy.random.RandomState, optional
        See :func:`imgaug.augmenters.meta.Augmenter.__init__`.

    Examples
    --------
    >>> import imgaug.augmenters as iaa
    >>> aug = iaa.CropToFixedSize(width=100, height=100)

    For image sides larger than ``100`` pixels, crop to ``100`` pixels. Do
    nothing for the other sides. The cropping amounts are randomly (and
    uniformly) distributed over the sides of the image.

    >>> aug = iaa.CropToFixedSize(width=100, height=100, position="center")

    For sides larger than ``100`` pixels, crop to ``100`` pixels. Do nothing
    for the other sides. The cropping amounts are always equally distributed
    over the left/right sides of the image (and analogously for top/bottom).

    >>> aug = iaa.Sequential([
    >>>     iaa.PadToFixedSize(width=100, height=100),
    >>>     iaa.CropToFixedSize(width=100, height=100)
    >>> ])

    Pad images smaller than ``100x100`` until they reach ``100x100``.
    Analogously, crop images larger than ``100x100`` until they reach
    ``100x100``. The output images therefore have a fixed size of ``100x100``.

    """

    def __init__(self, width, height, position="uniform",
                 name=None, deterministic=False, random_state=None):
        super(CropToFixedSize, self).__init__(
            name=name, deterministic=deterministic, random_state=random_state)
        self.size = width, height

        # Position of where to crop. The further to the top left this is,
        # the larger the share of pixels that will be cropped from the top
        # and left sides. I.e. set to (Deterministic(0.0), Deterministic(0.0))
        # to only crop at the top and left,
        # (Deterministic(1.0), Deterministic(1.0)) to only crop at the bottom
        # right. Analogously (0.5, 0.5) crops equally on both axis,
        # (0.0, 1.0) crops left and bottom, (1.0, 0.0) crops right and top.
        self.position = _handle_position_parameter(position)

    def _augment_images(self, images, random_state, parents, hooks):
        result = []
        nb_images = len(images)
        w, h = self.size
        offset_xs, offset_ys = self._draw_samples(nb_images, random_state)
        for i in sm.xrange(nb_images):
            image = images[i]
            height_image, width_image = image.shape[0:2]

            crop_image_top, crop_image_bottom = 0, 0
            crop_image_left, crop_image_right = 0, 0

            if height_image > h:
                crop_image_top = int(offset_ys[i] * (height_image - h))
                crop_image_bottom = height_image - h - crop_image_top

            if width_image > w:
                crop_image_left = int(offset_xs[i] * (width_image - w))
                crop_image_right = width_image - w - crop_image_left

            image = image[
                crop_image_top:height_image-crop_image_bottom,
                crop_image_left:width_image-crop_image_right,
                ...
            ]

            result.append(image)

        return result

    def _augment_keypoints(self, keypoints_on_images, random_state, parents,
                           hooks):
        result = []
        nb_images = len(keypoints_on_images)
        w, h = self.size
        offset_xs, offset_ys = self._draw_samples(nb_images, random_state)
        for i in sm.xrange(nb_images):
            keypoints_on_image = keypoints_on_images[i]
            height_image, width_image = keypoints_on_image.shape[0:2]

            crop_image_top, crop_image_bottom = 0, 0
            crop_image_left, crop_image_right = 0, 0

            if height_image > h:
                crop_image_top = int(offset_ys[i] * (height_image - h))
                crop_image_bottom = height_image - h - crop_image_top

            if width_image > w:
                crop_image_left = int(offset_xs[i] * (width_image - w))
                crop_image_right = width_image - w - crop_image_left

            keypoints_cropped = keypoints_on_image.shift(x=-crop_image_left,
                                                         y=-crop_image_top)
            keypoints_cropped.shape = (
                height_image - crop_image_top - crop_image_bottom,
                width_image - crop_image_left - crop_image_right
            ) + keypoints_on_image.shape[2:]

            result.append(keypoints_cropped)

        return result

    def _augment_polygons(self, polygons_on_images, random_state, parents,
                          hooks):
        return self._augment_polygons_as_keypoints(
            polygons_on_images, random_state, parents, hooks)

    def _augment_heatmaps(self, heatmaps, random_state, parents, hooks):
        nb_images = len(heatmaps)
        w, h = self.size
        offset_xs, offset_ys = self._draw_samples(nb_images, random_state)
        for i in sm.xrange(nb_images):
            height_img, width_img = heatmaps[i].shape[0:2]
            height_hm, width_hm = heatmaps[i].arr_0to1.shape[0:2]

            crop_img_t, crop_img_b = 0, 0
            crop_img_l, crop_img_r = 0, 0

            if height_img > h:
                crop_img_t = int(offset_ys[i] * (height_img - h))
                crop_img_b = height_img - h - crop_img_t

            if width_img > w:
                crop_img_l = int(offset_xs[i] * (width_img - w))
                crop_img_r = width_img - w - crop_img_l

            if (height_img, width_img) != (height_hm, width_hm):
                crop_top = _int_r(height_hm * (crop_img_t/height_img))
                crop_right = _int_r(width_hm * (crop_img_r/width_img))
                crop_bottom = _int_r(height_hm * (crop_img_b/height_img))
                crop_left = _int_r(width_hm * (crop_img_l/width_img))

                # TODO add test for zero-size prevention
                crop_top, crop_right, crop_bottom, crop_left = \
                    _crop_prevent_zero_size(
                        height_hm, width_hm,
                        crop_top, crop_right, crop_bottom, crop_left)
            else:
                crop_top = crop_img_t
                crop_right = crop_img_r
                crop_bottom = crop_img_b
                crop_left = crop_img_l

            heatmaps[i].arr_0to1 = \
                heatmaps[i].arr_0to1[crop_top:height_hm-crop_bottom,
                                     crop_left:width_hm-crop_right,
                                     :]

            heatmaps[i].shape = (
                heatmaps[i].shape[0] - crop_img_t - crop_img_b,
                heatmaps[i].shape[1] - crop_img_l - crop_img_r
            ) + heatmaps[i].shape[2:]

        return heatmaps

    def _augment_segmentation_maps(self, segmaps, random_state, parents, hooks):
        nb_images = len(segmaps)
        w, h = self.size
        offset_xs, offset_ys = self._draw_samples(nb_images, random_state)
        for i in sm.xrange(nb_images):
            height_img, width_img = segmaps[i].shape[0:2]
            height_sm, width_sm = segmaps[i].arr.shape[0:2]

            crop_img_t, crop_img_b = 0, 0
            crop_img_l, crop_img_r = 0, 0

            if height_img > h:
                crop_img_t = int(offset_ys[i] * (height_img - h))
                crop_img_b = height_img - h - crop_img_t

            if width_img > w:
                crop_img_l = int(offset_xs[i] * (width_img - w))
                crop_img_r = width_img - w - crop_img_l

            if (height_img, width_img) != (height_sm, width_sm):
                crop_top = _int_r(height_sm * (crop_img_t/height_img))
                crop_right = _int_r(width_sm * (crop_img_r/width_img))
                crop_bottom = _int_r(height_sm * (crop_img_b/height_img))
                crop_left = _int_r(width_sm * (crop_img_l/width_img))

                # TODO add test for zero-size prevention
                crop_top, crop_right, crop_bottom, crop_left = \
                    _crop_prevent_zero_size(
                        height_sm, width_sm,
                        crop_top, crop_right, crop_bottom, crop_left)
            else:
                crop_top = crop_img_t
                crop_right = crop_img_r
                crop_bottom = crop_img_b
                crop_left = crop_img_l

            segmaps[i].arr = segmaps[i].arr[crop_top:height_sm - crop_bottom,
                                            crop_left:width_sm-crop_right,
                                            :]

            segmaps[i].shape = (
                segmaps[i].shape[0] - crop_img_t - crop_img_b,
                segmaps[i].shape[1] - crop_img_l - crop_img_r
            ) + segmaps[i].shape[2:]

        return segmaps

    def _draw_samples(self, nb_images, random_state):
        rngs = random_state.duplicate(2)

        if isinstance(self.position, tuple):
            offset_xs = self.position[0].draw_samples(nb_images,
                                                      random_state=rngs[0])
            offset_ys = self.position[1].draw_samples(nb_images,
                                                      random_state=rngs[1])
        else:
            offsets = self.position.draw_samples((nb_images, 2),
                                                 random_state=rngs[0])
            offset_xs = offsets[:, 0]
            offset_ys = offsets[:, 1]

        offset_xs = 1.0 - offset_xs
        offset_ys = 1.0 - offset_ys

        return offset_xs, offset_ys

    def get_parameters(self):
        return [self.position]


class KeepSizeByResize(meta.Augmenter):
    """Resize images back to their input sizes after applying child augmenters.

    Combining this with e.g. a cropping augmenter as the child will lead to
    images being resized back to the input size after the crop operation was
    applied. Some augmenters have a ``keep_size`` argument that achieves the
    same goal (if set to ``True``), though this augmenter offers control over
    the interpolation mode and which augmentables to resize (images, heatmaps,
    segmentation maps).

    dtype support::

        See :func:`imgaug.imgaug.imresize_many_images`.

    Parameters
    ----------
    children : Augmenter or list of imgaug.augmenters.meta.Augmenter or None, optional
        One or more augmenters to apply to images. These augmenters may change
        the image size.

    interpolation : KeepSizeByResize.NO_RESIZE or {'nearest', 'linear', 'area', 'cubic'} or {cv2.INTER_NEAREST, cv2.INTER_LINEAR, cv2.INTER_AREA, cv2.INTER_CUBIC} or list of str or list of int or StochasticParameter, optional
        The interpolation mode to use when resizing images.
        Can take any value that :func:`imgaug.imgaug.imresize_single_image`
        accepts, e.g. ``cubic``.

            * If this is ``KeepSizeByResize.NO_RESIZE`` then images will not
              be resized.
            * If this is a single ``str``, it is expected to have one of the
              following values: ``nearest``, ``linear``, ``area``, ``cubic``.
            * If this is a single integer, it is expected to have a value
              identical to one of: ``cv2.INTER_NEAREST``,
              ``cv2.INTER_LINEAR``, ``cv2.INTER_AREA``, ``cv2.INTER_CUBIC``.
            * If this is a ``list`` of ``str`` or ``int``, it is expected that
              each ``str``/``int`` is one of the above mentioned valid ones.
              A random one of these values will be sampled per image.
            * If this is a ``StochasticParameter``, it will be queried once per
              call to ``_augment_images()`` and must return ``N`` ``str`` s or
              ``int`` s (matching the above mentioned ones) for ``N`` images.

    interpolation_heatmaps : KeepSizeByResize.SAME_AS_IMAGES or KeepSizeByResize.NO_RESIZE or {'nearest', 'linear', 'area', 'cubic'} or {cv2.INTER_NEAREST, cv2.INTER_LINEAR, cv2.INTER_AREA, cv2.INTER_CUBIC} or list of str or list of int or StochasticParameter, optional
        The interpolation mode to use when resizing heatmaps.
        Meaning and valid values are similar to `interpolation`. This
        parameter may also take the value ``KeepSizeByResize.SAME_AS_IMAGES``,
        which will lead to copying the interpolation modes used for the
        corresponding images. The value may also be returned on a per-image
        basis if `interpolation_heatmaps` is provided as a
        ``StochasticParameter`` or may be one possible value if it is
        provided as a ``list`` of ``str``.

    interpolation_segmaps : KeepSizeByResize.SAME_AS_IMAGES or KeepSizeByResize.NO_RESIZE or {'nearest', 'linear', 'area', 'cubic'} or {cv2.INTER_NEAREST, cv2.INTER_LINEAR, cv2.INTER_AREA, cv2.INTER_CUBIC} or list of str or list of int or StochasticParameter, optional
        The interpolation mode to use when resizing segmentation maps.
        Similar to `interpolation_heatmaps`.
        **Note**: For segmentation maps, only ``NO_RESIZE`` or nearest
        neighbour interpolation (i.e. ``nearest``) make sense in the vast
        majority of all cases.

    name : None or str, optional
        See :func:`imgaug.augmenters.meta.Augmenter.__init__`.

    deterministic : bool, optional
        See :func:`imgaug.augmenters.meta.Augmenter.__init__`.

    random_state : None or int or imgaug.random.RNG or numpy.random.Generator or numpy.random.bit_generator.BitGenerator or numpy.random.SeedSequence or numpy.random.RandomState, optional
        See :func:`imgaug.augmenters.meta.Augmenter.__init__`.

    Examples
    --------
    >>> import imgaug.augmenters as iaa
    >>> aug = iaa.KeepSizeByResize(
    >>>     iaa.Crop((20, 40), keep_size=False)
    >>> )

    Apply random cropping to input images, then resize them back to their
    original input sizes. The resizing is done using this augmenter instead
    of the corresponding internal resizing operation in ``Crop``.

    >>> aug = iaa.KeepSizeByResize(
    >>>     iaa.Crop((20, 40), keep_size=False),
    >>>     interpolation="nearest"
    >>> )

    Same as in the previous example, but images are now always resized using
    nearest neighbour interpolation.

    >>> aug = iaa.KeepSizeByResize(
    >>>     iaa.Crop((20, 40), keep_size=False),
    >>>     interpolation=["nearest", "cubic"],
    >>>     interpolation_heatmaps=iaa.KeepSizeByResize.SAME_AS_IMAGES,
    >>>     interpolation_segmaps=iaa.KeepSizeByResize.NO_RESIZE
    >>> )

    Similar to the previous example, but images are now sometimes resized
    using linear interpolation and sometimes using nearest neighbour
    interpolation. Heatmaps are resized using the same interpolation as was
    used for the corresponding image. Segmentation maps are not resized and
    will therefore remain at their size after cropping.

    """

    NO_RESIZE = "NO_RESIZE"
    SAME_AS_IMAGES = "SAME_AS_IMAGES"

    def __init__(self, children,
                 interpolation="cubic",
                 interpolation_heatmaps=SAME_AS_IMAGES,
                 interpolation_segmaps="nearest",
                 name=None, deterministic=False, random_state=None):
        super(KeepSizeByResize, self).__init__(
            name=name, deterministic=deterministic, random_state=random_state)
        self.children = children

        def _validate_param(val, allow_same_as_images):
            valid_ips_and_resize = ia.IMRESIZE_VALID_INTERPOLATIONS \
                                  + [KeepSizeByResize.NO_RESIZE]
            if allow_same_as_images and val == self.SAME_AS_IMAGES:
                return self.SAME_AS_IMAGES
            elif val in valid_ips_and_resize:
                return iap.Deterministic(val)
            elif isinstance(val, list):
                assert len(val) > 0, (
                    "Expected a list of at least one interpolation method. "
                    "Got an empty list.")
                valid_ips_here = valid_ips_and_resize
                if allow_same_as_images:
                    valid_ips_here = valid_ips_here \
                                     + [KeepSizeByResize.SAME_AS_IMAGES]
                only_valid_ips = all([ip in valid_ips_here for ip in val])
                assert only_valid_ips, (
                    "Expected each interpolations to be one of '%s', got "
                    "'%s'." % (str(valid_ips_here), str(val)))
                return iap.Choice(val)
            elif isinstance(val, iap.StochasticParameter):
                return val
            else:
                raise Exception(
                    "Expected interpolation to be one of '%s' or a list of "
                    "these values or a StochasticParameter. Got type %s." % (
                        str(ia.IMRESIZE_VALID_INTERPOLATIONS), type(val)))

        self.children = meta.handle_children_list(children, self.name, "then")
        self.interpolation = _validate_param(interpolation, False)
        self.interpolation_heatmaps = _validate_param(interpolation_heatmaps,
                                                      True)
        self.interpolation_segmaps = _validate_param(interpolation_segmaps,
                                                     True)

    def _draw_samples(self, nb_images, random_state):
        rngs = random_state.duplicate(3)
        interpolations = self.interpolation.draw_samples((nb_images,),
                                                         random_state=rngs[0])

        if self.interpolation_heatmaps == KeepSizeByResize.SAME_AS_IMAGES:
            interpolations_heatmaps = np.copy(interpolations)
        else:
            interpolations_heatmaps = self.interpolation_heatmaps.draw_samples(
                (nb_images,), random_state=rngs[1]
            )

            # Note that `interpolations_heatmaps == self.SAME_AS_IMAGES`
            # works here only if the datatype of the array is such that it
            # may contain strings. It does not work properly for e.g.
            # integer arrays and will produce a single bool output, even
            # for arrays with more than one entry.
            same_as_imgs_idx = [ip == self.SAME_AS_IMAGES
                                for ip in interpolations_heatmaps]

            interpolations_heatmaps[same_as_imgs_idx] = \
                interpolations[same_as_imgs_idx]

        if self.interpolation_segmaps == KeepSizeByResize.SAME_AS_IMAGES:
            interpolations_segmaps = np.copy(interpolations)
        else:
            # TODO This used previously the same seed as the heatmaps part
            #      leading to the same sampled values. Was that intentional?
            #      Doesn't look like it should be that way.
            interpolations_segmaps = self.interpolation_segmaps.draw_samples(
                (nb_images,), random_state=rngs[2]
            )

            # Note that `interpolations_heatmaps == self.SAME_AS_IMAGES`
            # works here only if the datatype of the array is such that it
            # may contain strings. It does not work properly for e.g.
            # integer arrays and will produce a single bool output, even
            # for arrays with more than one entry.
            same_as_imgs_idx = [ip == self.SAME_AS_IMAGES
                                for ip in interpolations_segmaps]

            interpolations_segmaps[same_as_imgs_idx] = \
                interpolations[same_as_imgs_idx]

        return interpolations, interpolations_heatmaps, interpolations_segmaps

    def _is_propagating(self, augmentables, parents, hooks):
        return (
            hooks is None
            or hooks.is_propagating(
                augmentables, augmenter=self, parents=parents, default=True)
        )

    def _augment_images(self, images, random_state, parents, hooks):
        input_was_array = ia.is_np_array(images)
        if self._is_propagating(images, parents, hooks):
            interpolations, _, _ = self._draw_samples(len(images),
                                                      random_state)
            input_shapes = [image.shape[0:2] for image in images]

            images_aug = self.children.augment_images(
                images=images,
                parents=parents + [self],
                hooks=hooks
            )

            gen = zip(images_aug, interpolations, input_shapes)
            result = []
            for image_aug, interpolation, input_shape in gen:
                if interpolation == KeepSizeByResize.NO_RESIZE:
                    result.append(image_aug)
                else:
                    result.append(
                        ia.imresize_single_image(image_aug, input_shape[0:2],
                                                 interpolation))

            if input_was_array:
                # note here that NO_RESIZE can have led to different shapes
                nb_shapes = len(set([image.shape for image in result]))
                if nb_shapes == 1:
                    result = np.array(result, dtype=images.dtype)

        else:
            result = images
        return result

    def _augment_heatmaps(self, heatmaps, random_state, parents, hooks):
        if self._is_propagating(heatmaps, parents, hooks):
            nb_heatmaps = len(heatmaps)
            _, interpolations_heatmaps, _ = self._draw_samples(
                nb_heatmaps, random_state)
            input_arr_shapes = [heatmaps_i.arr_0to1.shape
                                for heatmaps_i in heatmaps]

            # augment according to if and else list
            heatmaps_aug = self.children.augment_heatmaps(
                heatmaps,
                parents=parents + [self],
                hooks=hooks
            )

            result = []
            gen = zip(heatmaps, heatmaps_aug, interpolations_heatmaps,
                      input_arr_shapes)
            for heatmap, heatmap_aug, interpolation, input_arr_shape in gen:
                if interpolation == "NO_RESIZE":
                    result.append(heatmap_aug)
                else:
                    heatmap_aug = heatmap_aug.resize(
                        input_arr_shape[0:2], interpolation=interpolation)
                    heatmap_aug.shape = heatmap.shape
                    result.append(heatmap_aug)
        else:
            result = heatmaps

        return result

    def _augment_segmentation_maps(self, segmaps, random_state, parents, hooks):
        if self._is_propagating(segmaps, parents, hooks):
            nb_segmaps = len(segmaps)
            _, _, interpolations_segmaps = self._draw_samples(nb_segmaps,
                                                              random_state)
            input_arr_shapes = [segmaps_i.arr.shape for segmaps_i in segmaps]

            # augment according to if and else list
            segmaps_aug = self.children.augment_segmentation_maps(
                segmaps,
                parents=parents + [self],
                hooks=hooks
            )

            result = []
            gen = zip(segmaps, segmaps_aug, interpolations_segmaps,
                      input_arr_shapes)
            for segmaps, segmaps_aug, interpolation, input_arr_shape in gen:
                if interpolation == "NO_RESIZE":
                    result.append(segmaps_aug)
                else:
                    segmaps_aug = segmaps_aug.resize(
                        input_arr_shape[0:2], interpolation=interpolation)
                    segmaps_aug.shape = segmaps.shape
                    result.append(segmaps_aug)
        else:
            result = segmaps

        return result

    def _augment_keypoints(self, keypoints_on_images, random_state, parents,
                           hooks):
        if self._is_propagating(keypoints_on_images, parents, hooks):
            interpolations, _, _ = self._draw_samples(
                len(keypoints_on_images), random_state)
            input_shapes = [kpsoi_i.shape for kpsoi_i in keypoints_on_images]

            # augment according to if and else list
            kps_aug = self.children.augment_keypoints(
                keypoints_on_images=keypoints_on_images,
                parents=parents + [self],
                hooks=hooks
            )

            result = []
            gen = zip(keypoints_on_images, kps_aug, interpolations,
                      input_shapes)
            for kps, kps_aug, interpolation, input_shape in gen:
                if interpolation == KeepSizeByResize.NO_RESIZE:
                    result.append(kps_aug)
                else:
                    result.append(kps_aug.on(input_shape))
        else:
            result = keypoints_on_images

        return result

    def _augment_polygons(self, polygons_on_images, random_state, parents,
                          hooks):
        return self._augment_polygons_as_keypoints(
            polygons_on_images, random_state, parents, hooks)

    def _to_deterministic(self):
        aug = self.copy()
        aug.children = aug.children.to_deterministic()
        aug.deterministic = True
        aug.random_state = self.random_state.derive_rng_()
        return aug

    def get_parameters(self):
        return [self.interpolation, self.interpolation_heatmaps]

    def get_children_lists(self):
        return [self.children]

    def __str__(self):
        pattern = (
            "%s("
            "interpolation=%s, "
            "interpolation_heatmaps=%s, "
            "name=%s, "
            "children=%s, "
            "deterministic=%s"
            ")")
        return pattern % (
            self.__class__.__name__, self.interpolation,
            self.interpolation_heatmaps, self.name, self.children,
            self.deterministic)
