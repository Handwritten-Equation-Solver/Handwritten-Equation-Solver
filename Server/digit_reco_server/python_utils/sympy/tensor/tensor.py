"""
This module defines tensors with abstract index notation.

The abstract index notation has been first formalized by Penrose.

Tensor indices are formal objects, with a tensor type; there is no
notion of index range, it is only possible to assign the dimension,
used to trace the Kronecker delta; the dimension can be a Symbol.

The Einstein summation convention is used.
The covariant indices are indicated with a minus sign in front of the index.

For instance the tensor ``t = p(a)*A(b,c)*q(-c)`` has the index ``c``
contracted.

A tensor expression ``t`` can be called; called with its
indices in sorted order it is equal to itself:
in the above example ``t(a, b) == t``;
one can call ``t`` with different indices; ``t(c, d) == p(c)*A(d,a)*q(-a)``.

The contracted indices are dummy indices, internally they have no name,
the indices being represented by a graph-like structure.

Tensors are put in canonical form using ``canon_bp``, which uses
the Butler-Portugal algorithm for canonicalization using the monoterm
symmetries of the tensors.

If there is a (anti)symmetric metric, the indices can be raised and
lowered when the tensor is put in canonical form.
"""

from __future__ import print_function, division

from collections import defaultdict
import itertools
from sympy import Matrix, Rational, prod, Integer
from sympy.combinatorics.tensor_can import get_symmetric_group_sgs, \
    bsgs_direct_product, canonicalize, riemann_bsgs
from sympy.core import Basic, sympify, Add, S
from sympy.core.compatibility import string_types, reduce, range, SYMPY_INTS
from sympy.core.containers import Tuple
from sympy.core.decorators import deprecated
from sympy.core.symbol import Symbol, symbols
from sympy.core.sympify import CantSympify
from sympy.matrices import eye


class TIDS(CantSympify):
    """
    DEPRECATED CLASS: DO NOT USE.

    Tensor-index data structure. This contains internal data structures about
    components of a tensor expression, its free and dummy indices.

    To create a ``TIDS`` object via the standard constructor, the required
    arguments are

    WARNING: this class is meant as an internal representation of tensor data
    structures and should not be directly accessed by end users.

    Parameters
    ==========

    components : ``TensorHead`` objects representing the components of the tensor expression.

    free : Free indices in their internal representation.

    dum : Dummy indices in their internal representation.

    Examples
    ========

    >>> from sympy.tensor.tensor import TensorIndexType, tensor_indices, TIDS, tensorhead
    >>> Lorentz = TensorIndexType('Lorentz', dummy_fmt='L')
    >>> m0, m1, m2, m3 = tensor_indices('m0,m1,m2,m3', Lorentz)
    >>> T = tensorhead('T', [Lorentz]*4, [[1]*4])
    >>> TIDS([T], [(m0, 0, 0), (m3, 3, 0)], [(1, 2, 0, 0)])
    TIDS([T(Lorentz,Lorentz,Lorentz,Lorentz)], [(m0, 0, 0), (m3, 3, 0)], [(1, 2, 0, 0)])

    Notes
    =====

    In short, this has created the components, free and dummy indices for
    the internal representation of a tensor T(m0, m1, -m1, m3).

    Free indices are represented as a list of triplets. The elements of
    each triplet identify a single free index and are

    1. TensorIndex object
    2. position inside the component
    3. component number

    Dummy indices are represented as a list of 4-plets. Each 4-plet stands
    for couple for contracted indices, their original TensorIndex is not
    stored as it is no longer required. The four elements of the 4-plet
    are

    1. position inside the component of the first index.
    2. position inside the component of the second index.
    3. component number of the first index.
    4. component number of the second index.

    """

    def __init__(self, components, free, dum):
        self.components = components
        self.free = free
        self.dum = dum
        self._ext_rank = len(self.free) + 2*len(self.dum)
        self.dum.sort(key=lambda x: (x[2], x[0]))

    def get_tensors(self):
        """
        Get a list of ``Tensor`` objects having the same ``TIDS`` if multiplied
        by one another.
        """
        indices = self.get_indices()
        components = self.components
        tensors = [None for i in components]  # pre-allocate list
        ind_pos = 0
        for i, component in enumerate(components):
            prev_pos = ind_pos
            ind_pos += component.rank
            tensors[i] = Tensor(component, indices[prev_pos:ind_pos])
        return tensors

    def get_components_with_free_indices(self):
        """
        Get a list of components with their associated indices.

        Examples
        ========

        >>> from sympy.tensor.tensor import TensorIndexType, tensor_indices, TIDS, tensorhead
        >>> Lorentz = TensorIndexType('Lorentz', dummy_fmt='L')
        >>> m0, m1, m2, m3 = tensor_indices('m0,m1,m2,m3', Lorentz)
        >>> T = tensorhead('T', [Lorentz]*4, [[1]*4])
        >>> A = tensorhead('A', [Lorentz], [[1]])
        >>> t = TIDS.from_components_and_indices([T], [m0, m1, -m1, m3])
        >>> t.get_components_with_free_indices()
        [(T(Lorentz,Lorentz,Lorentz,Lorentz), [(m0, 0, 0), (m3, 3, 0)])]
        """
        components = self.components
        ret_comp = []

        free_counter = 0
        if len(self.free) == 0:
            return [(comp, []) for comp in components]

        for i, comp in enumerate(components):
            c_free = []
            while free_counter < len(self.free):
                if not self.free[free_counter][2] == i:
                    break

                c_free.append(self.free[free_counter])
                free_counter += 1

                if free_counter >= len(self.free):
                    break
            ret_comp.append((comp, c_free))

        return ret_comp

    @staticmethod
    def from_components_and_indices(components, indices):
        """
        Create a new ``TIDS`` object from ``components`` and ``indices``

        ``components``  ``TensorHead`` objects representing the components
                        of the tensor expression.

        ``indices``     ``TensorIndex`` objects, the indices. Contractions are
                        detected upon construction.

        """
        tids = None
        cur_pos = 0
        for i in components:
            tids_sing = TIDS([i], *TIDS.free_dum_from_indices(*indices[cur_pos:cur_pos+i.rank]))
            if tids is None:
                tids = tids_sing
            else:
                tids *= tids_sing
            cur_pos += i.rank

        if tids is None:
            tids = TIDS([], [], [])

        tids.free.sort(key=lambda x: x[0].name)
        tids.dum.sort()

        return tids

    @deprecated(useinstead="get_indices", issue=12857, deprecated_since_version="0.7.5")
    def to_indices(self):
        return self.get_indices()

    @staticmethod
    def free_dum_from_indices(*indices):
        """
        Convert ``indices`` into ``free``, ``dum`` for single component tensor

        ``free``     list of tuples ``(index, pos, 0)``,
                     where ``pos`` is the position of index in
                     the list of indices formed by the component tensors

        ``dum``      list of tuples ``(pos_contr, pos_cov, 0, 0)``

        Examples
        ========

        >>> from sympy.tensor.tensor import TensorIndexType, tensor_indices, TIDS
        >>> Lorentz = TensorIndexType('Lorentz', dummy_fmt='L')
        >>> m0, m1, m2, m3 = tensor_indices('m0,m1,m2,m3', Lorentz)
        >>> TIDS.free_dum_from_indices(m0, m1, -m1, m3)
        ([(m0, 0, 0), (m3, 3, 0)], [(1, 2, 0, 0)])
        """
        n = len(indices)
        if n == 1:
            return [(indices[0], 0, 0)], []

        # find the positions of the free indices and of the dummy indices
        free = [True]*len(indices)
        index_dict = {}
        dum = []
        for i, index in enumerate(indices):
            name = index._name
            typ = index.tensor_index_type
            contr = index._is_up
            if (name, typ) in index_dict:
                # found a pair of dummy indices
                is_contr, pos = index_dict[(name, typ)]
                # check consistency and update free
                if is_contr:
                    if contr:
                        raise ValueError('two equal contravariant indices in slots %d and %d' %(pos, i))
                    else:
                        free[pos] = False
                        free[i] = False
                else:
                    if contr:
                        free[pos] = False
                        free[i] = False
                    else:
                        raise ValueError('two equal covariant indices in slots %d and %d' %(pos, i))
                if contr:
                    dum.append((i, pos, 0, 0))
                else:
                    dum.append((pos, i, 0, 0))
            else:
                index_dict[(name, typ)] = index._is_up, i

        free = [(index, i, 0) for i, index in enumerate(indices) if free[i]]
        free.sort()
        return free, dum

    @staticmethod
    def _check_matrix_indices(f_free, g_free, nc1):
        # This "private" method checks matrix indices.
        # Matrix indices are special as there are only two, and observe
        # anomalous substitution rules to determine contractions.

        dum = []
        # make sure that free indices appear in the same order as in their component:
        f_free.sort(key=lambda x: (x[2], x[1]))
        g_free.sort(key=lambda x: (x[2], x[1]))
        matrix_indices_storage = {}
        transform_right_to_left = {}
        f_pop_pos = []
        g_pop_pos = []
        for free_pos, (ind, i, c) in enumerate(f_free):
            index_type = ind.tensor_index_type
            if ind not in (index_type.auto_left, -index_type.auto_right):
                continue
            matrix_indices_storage[ind] = (free_pos, i, c)

        for free_pos, (ind, i, c) in enumerate(g_free):
            index_type = ind.tensor_index_type
            if ind not in (index_type.auto_left, -index_type.auto_right):
                continue

            if ind == index_type.auto_left:
                if -index_type.auto_right in matrix_indices_storage:
                    other_pos, other_i, other_c = matrix_indices_storage.pop(-index_type.auto_right)
                    dum.append((other_i, i, other_c, c + nc1))
                    # mark to remove other_pos and free_pos from free:
                    g_pop_pos.append(free_pos)
                    f_pop_pos.append(other_pos)
                    continue
                if ind in matrix_indices_storage:
                    other_pos, other_i, other_c = matrix_indices_storage.pop(ind)
                    dum.append((other_i, i, other_c, c + nc1))
                    # mark to remove other_pos and free_pos from free:
                    g_pop_pos.append(free_pos)
                    f_pop_pos.append(other_pos)
                    transform_right_to_left[-index_type.auto_right] = c
                    continue

            if ind in transform_right_to_left:
                other_c = transform_right_to_left.pop(ind)
                if c == other_c:
                    g_free[free_pos] = (index_type.auto_left, i, c)

        for i in reversed(sorted(f_pop_pos)):
            f_free.pop(i)
        for i in reversed(sorted(g_pop_pos)):
            g_free.pop(i)
        return dum

    @staticmethod
    def mul(f, g):
        """
        The algorithms performing the multiplication of two ``TIDS`` instances.

        In short, it forms a new ``TIDS`` object, joining components and indices,
        checking that abstract indices are compatible, and possibly contracting
        them.
        """
        index_up = lambda u: u if u.is_up else -u

        f_free = f.free[:]
        g_free = g.free[:]
        nc1 = len(f.components)
        dum = TIDS._check_matrix_indices(f_free, g_free, nc1)

        # find out which free indices of f and g are contracted
        free_dict1 = {i if i.is_up else -i: (pos, cpos, i) for i, pos, cpos in f_free}
        free_dict2 = {i if i.is_up else -i: (pos, cpos, i) for i, pos, cpos in g_free}
        free_names = set(free_dict1.keys()) & set(free_dict2.keys())
        # find the new `free` and `dum`

        dum2 = [(i1, i2, c1 + nc1, c2 + nc1) for i1, i2, c1, c2 in g.dum]
        free1 = [(ind, i, c) for ind, i, c in f_free if index_up(ind) not in free_names]
        free2 = [(ind, i, c + nc1) for ind, i, c in g_free if index_up(ind) not in free_names]
        free = free1 + free2
        dum.extend(f.dum + dum2)
        for name in free_names:
            ipos1, cpos1, ind1 = free_dict1[name]
            ipos2, cpos2, ind2 = free_dict2[name]
            cpos2 += nc1
            if ind1._is_up == ind2._is_up:
                raise ValueError('wrong index construction {0}'.format(ind1))
            if ind1._is_up:
                new_dummy = (ipos1, ipos2, cpos1, cpos2)
            else:
                new_dummy = (ipos2, ipos1, cpos2, cpos1)
            dum.append(new_dummy)
        return (f.components + g.components, free, dum)

    def __mul__(self, other):
        return TIDS(*self.mul(self, other))

    def __str__(self):
        return "TIDS({0}, {1}, {2})".format(self.components, self.free, self.dum)

    def __repr__(self):
        return self.__str__()

    def sorted_components(self):
        """
        Returns a ``TIDS`` with sorted components

        The sorting is done taking into account the commutation group
        of the component tensors.
        """
        from sympy.combinatorics.permutations import _af_invert
        cv = list(zip(self.components, range(len(self.components))))
        sign = 1
        n = len(cv) - 1
        for i in range(n):
            for j in range(n, i, -1):
                c = cv[j-1][0].commutes_with(cv[j][0])
                if c not in [0, 1]:
                    continue
                if (cv[j-1][0].index_types, cv[j-1][0]._name) > \
                        (cv[j][0].index_types, cv[j][0]._name):
                    cv[j-1], cv[j] = cv[j], cv[j-1]
                    if c:
                        sign = -sign

        # perm_inv[new_pos] = old_pos
        components = [x[0] for x in cv]
        perm_inv = [x[1] for x in cv]
        perm = _af_invert(perm_inv)
        free = [(ind, i, perm[c]) for ind, i, c in self.free]
        free.sort()
        dum = [(i1, i2, perm[c1], perm[c2]) for i1, i2, c1, c2 in self.dum]
        dum.sort(key=lambda x: components[x[2]].index_types[x[0]])

        return TIDS(components, free, dum), sign

    def _get_sorted_free_indices_for_canon(self):
        sorted_free = self.free[:]
        sorted_free.sort(key=lambda x: x[0])
        return sorted_free

    def _get_sorted_dum_indices_for_canon(self):
        return sorted(self.dum, key=lambda x: (x[2], x[0]))

    def canon_args(self):
        """
        Returns ``(g, dummies, msym, v)``, the entries of ``canonicalize``

        see ``canonicalize`` in ``tensor_can.py``
        """
        # to be called after sorted_components
        from sympy.combinatorics.permutations import _af_new
#         types = list(set(self._types))
#         types.sort(key = lambda x: x._name)
        n = self._ext_rank
        g = [None]*n + [n, n+1]
        pos = 0
        vpos = []
        components = self.components
        for t in components:
            vpos.append(pos)
            pos += t._rank
        # ordered indices: first the free indices, ordered by types
        # then the dummy indices, ordered by types and contravariant before
        # covariant
        # g[position in tensor] = position in ordered indices
        for i, (indx, ipos, cpos) in enumerate(self._get_sorted_free_indices_for_canon()):
            pos = vpos[cpos] + ipos
            g[pos] = i
        pos = len(self.free)
        j = len(self.free)
        dummies = []
        prev = None
        a = []
        msym = []
        for ipos1, ipos2, cpos1, cpos2 in self._get_sorted_dum_indices_for_canon():
            pos1 = vpos[cpos1] + ipos1
            pos2 = vpos[cpos2] + ipos2
            g[pos1] = j
            g[pos2] = j + 1
            j += 2
            typ = components[cpos1].index_types[ipos1]
            if typ != prev:
                if a:
                    dummies.append(a)
                a = [pos, pos + 1]
                prev = typ
                msym.append(typ.metric_antisym)
            else:
                a.extend([pos, pos + 1])
            pos += 2
        if a:
            dummies.append(a)
        numtyp = []
        prev = None
        for t in components:
            if t == prev:
                numtyp[-1][1] += 1
            else:
                prev = t
                numtyp.append([prev, 1])
        v = []
        for h, n in numtyp:
            if h._comm == 0 or h._comm == 1:
                comm = h._comm
            else:
                comm = TensorManager.get_comm(h._comm, h._comm)
            v.append((h._symmetry.base, h._symmetry.generators, n, comm))
        return _af_new(g), dummies, msym, v

    def perm2tensor(self, g, canon_bp=False):
        """
        Returns a ``TIDS`` instance corresponding to the permutation ``g``

        ``g``  permutation corresponding to the tensor in the representation
        used in canonicalization

        ``canon_bp``   if True, then ``g`` is the permutation
        corresponding to the canonical form of the tensor
        """
        vpos = []
        components = self.components
        pos = 0
        for t in components:
            vpos.append(pos)
            pos += t._rank
        sorted_free = [i[0] for i in self._get_sorted_free_indices_for_canon()]
        nfree = len(sorted_free)
        rank = self._ext_rank
        dum = [[None]*4 for i in range((rank - nfree)//2)]
        free = []
        icomp = -1
        for i in range(rank):
            if i in vpos:
                icomp += vpos.count(i)
                pos0 = i
            ipos = i - pos0
            gi = g[i]
            if gi < nfree:
                ind = sorted_free[gi]
                free.append((ind, ipos, icomp))
            else:
                j = gi - nfree
                idum, cov = divmod(j, 2)
                if cov:
                    dum[idum][1] = ipos
                    dum[idum][3] = icomp
                else:
                    dum[idum][0] = ipos
                    dum[idum][2] = icomp
        dum = [tuple(x) for x in dum]

        return TIDS(components, free, dum)

    def get_indices(self):
        """
        Get a list of indices, creating new tensor indices to complete dummy indices.
        """
        components = self.components
        free = self.free
        dum = self.dum
        indices = [None]*self._ext_rank
        start = 0
        pos = 0
        vpos = []
        for t in components:
            vpos.append(pos)
            pos += t.rank
        cdt = defaultdict(int)
        # if the free indices have names with dummy_fmt, start with an
        # index higher than those for the dummy indices
        # to avoid name collisions
        for indx, ipos, cpos in free:
            if indx._name.split('_')[0] == indx.tensor_index_type._dummy_fmt[:-3]:
                cdt[indx.tensor_index_type] = max(cdt[indx.tensor_index_type], int(indx._name.split('_')[1]) + 1)
            start = vpos[cpos]
            indices[start + ipos] = indx
        for ipos1, ipos2, cpos1, cpos2 in dum:
            start1 = vpos[cpos1]
            start2 = vpos[cpos2]
            typ1 = components[cpos1].index_types[ipos1]
            assert typ1 == components[cpos2].index_types[ipos2]
            fmt = typ1._dummy_fmt
            nd = cdt[typ1]
            indices[start1 + ipos1] = TensorIndex(fmt % nd, typ1)
            indices[start2 + ipos2] = TensorIndex(fmt % nd, typ1, False)
            cdt[typ1] += 1
        return indices

    def contract_metric(self, g):
        """
        Returns new TIDS and sign.

        Sign is either 1 or -1, to correct the sign after metric contraction
        (for spinor indices).
        """
        components = self.components
        antisym = g.index_types[0].metric_antisym
        #if not any(x == g for x in components):
        #    return self
        # list of positions of the metric ``g``
        gpos = [i for i, x in enumerate(components) if x == g]
        if not gpos:
            return self, 1
        sign = 1
        dum = self.dum[:]
        free = self.free[:]
        elim = set()
        for gposx in gpos:
            if gposx in elim:
                continue
            free1 = [x for x in free if x[-1] == gposx]
            dum1 = [x for x in dum if x[-2] == gposx or x[-1] == gposx]
            if not dum1:
                continue
            elim.add(gposx)
            if len(dum1) == 2:
                if not antisym:
                    dum10, dum11 = dum1
                    if dum10[3] == gposx:
                        # the index with pos p0 and component c0 is contravariant
                        c0 = dum10[2]
                        p0 = dum10[0]
                    else:
                        # the index with pos p0 and component c0 is covariant
                        c0 = dum10[3]
                        p0 = dum10[1]
                    if dum11[3] == gposx:
                        # the index with pos p1 and component c1 is contravariant
                        c1 = dum11[2]
                        p1 = dum11[0]
                    else:
                        # the index with pos p1 and component c1 is covariant
                        c1 = dum11[3]
                        p1 = dum11[1]
                    dum.append((p0, p1, c0, c1))
                else:
                    dum10, dum11 = dum1
                    # change the sign to bring the indices of the metric to contravariant
                    # form; change the sign if dum10 has the metric index in position 0
                    if dum10[3] == gposx:
                        # the index with pos p0 and component c0 is contravariant
                        c0 = dum10[2]
                        p0 = dum10[0]
                        if dum10[1] == 1:
                            sign = -sign
                    else:
                        # the index with pos p0 and component c0 is covariant
                        c0 = dum10[3]
                        p0 = dum10[1]
                        if dum10[0] == 0:
                            sign = -sign
                    if dum11[3] == gposx:
                        # the index with pos p1 and component c1 is contravariant
                        c1 = dum11[2]
                        p1 = dum11[0]
                        sign = -sign
                    else:
                        # the index with pos p1 and component c1 is covariant
                        c1 = dum11[3]
                        p1 = dum11[1]
                    dum.append((p0, p1, c0, c1))

            elif len(dum1) == 1:
                if not antisym:
                    dp0, dp1, dc0, dc1 = dum1[0]
                    if dc0 == dc1:
                        # g(i, -i)
                        typ = g.index_types[0]
                        if typ._dim is None:
                            raise ValueError('dimension not assigned')
                        sign = sign*typ._dim

                    else:
                        # g(i0, i1)*p(-i1)
                        if dc0 == gposx:
                            p1 = dp1
                            c1 = dc1
                        else:
                            p1 = dp0
                            c1 = dc0
                        ind, p, c = free1[0]
                        free.append((ind, p1, c1))
                else:
                    dp0, dp1, dc0, dc1 = dum1[0]
                    if dc0 == dc1:
                        # g(i, -i)
                        typ = g.index_types[0]
                        if typ._dim is None:
                            raise ValueError('dimension not assigned')
                        sign = sign*typ._dim

                        if dp0 < dp1:
                            # g(i, -i) = -D with antisymmetric metric
                            sign = -sign
                    else:
                        # g(i0, i1)*p(-i1)
                        if dc0 == gposx:
                            p1 = dp1
                            c1 = dc1
                            if dp0 == 0:
                                sign = -sign
                        else:
                            p1 = dp0
                            c1 = dc0
                        ind, p, c = free1[0]
                        free.append((ind, p1, c1))
            dum = [x for x in dum if x not in dum1]
            free = [x for x in free if x not in free1]

        shift = 0
        shifts = [0]*len(components)
        for i in range(len(components)):
            if i in elim:
                shift += 1
                continue
            shifts[i] = shift
        free = [(ind, p, c - shifts[c]) for (ind, p, c) in free if c not in elim]
        dum = [(p0, p1, c0 - shifts[c0], c1 - shifts[c1]) for  i, (p0, p1, c0, c1) in enumerate(dum) if c0 not in elim and c1 not in elim]
        components = [c for i, c in enumerate(components) if i not in elim]
        tids = TIDS(components, free, dum)
        return tids, sign


class _IndexStructure(CantSympify):
    """
    This class handles the indices (free and dummy ones). It contains the
    algorithms to manage the dummy indices replacements and contractions of
    free indices under multiplications of tensor expressions, as well as stuff
    related to canonicalization sorting, getting the permutation of the
    expression and so on. It also includes tools to get the ``TensorIndex``
    objects corresponding to the given index structure.
    """

    def __init__(self, free, dum, index_types, indices, canon_bp=False):
        self.free = free
        self.dum = dum
        self.index_types = index_types
        self.indices = indices
        self._ext_rank = len(self.free) + 2*len(self.dum)
        self.dum.sort(key=lambda x: x[0])

    @staticmethod
    def from_indices(*indices):
        """
        Create a new ``_IndexStructure`` object from a list of ``indices``

        ``indices``     ``TensorIndex`` objects, the indices. Contractions are
                        detected upon construction.

        Examples
        ========

        >>> from sympy.tensor.tensor import TensorIndexType, tensor_indices, _IndexStructure
        >>> Lorentz = TensorIndexType('Lorentz', dummy_fmt='L')
        >>> m0, m1, m2, m3 = tensor_indices('m0,m1,m2,m3', Lorentz)
        >>> _IndexStructure.from_indices(m0, m1, -m1, m3)
        _IndexStructure([(m0, 0), (m3, 3)], [(1, 2)], [Lorentz, Lorentz, Lorentz, Lorentz])

        In case of many components the same indices have slightly different
        indexes:

        >>> _IndexStructure.from_indices(m0, m1, -m1, m3)
        _IndexStructure([(m0, 0), (m3, 3)], [(1, 2)], [Lorentz, Lorentz, Lorentz, Lorentz])
        """
        free, dum = _IndexStructure._free_dum_from_indices(*indices)
        index_types = [i.tensor_index_type for i in indices]
        indices = _IndexStructure._replace_dummy_names(indices, free, dum)
        return _IndexStructure(free, dum, index_types, indices)

    @staticmethod
    def from_components_free_dum(components, free, dum):
        index_types = []
        for component in components:
            index_types.extend(component.index_types)
        indices = _IndexStructure.generate_indices_from_free_dum_index_types(free, dum, index_types)
        return _IndexStructure(free, dum, index_types, indices)

    @staticmethod
    def _free_dum_from_indices(*indices):
        """
        Convert ``indices`` into ``free``, ``dum`` for single component tensor

        ``free``     list of tuples ``(index, pos, 0)``,
                     where ``pos`` is the position of index in
                     the list of indices formed by the component tensors

        ``dum``      list of tuples ``(pos_contr, pos_cov, 0, 0)``

        Examples
        ========

        >>> from sympy.tensor.tensor import TensorIndexType, tensor_indices, \
            _IndexStructure
        >>> Lorentz = TensorIndexType('Lorentz', dummy_fmt='L')
        >>> m0, m1, m2, m3 = tensor_indices('m0,m1,m2,m3', Lorentz)
        >>> _IndexStructure._free_dum_from_indices(m0, m1, -m1, m3)
        ([(m0, 0), (m3, 3)], [(1, 2)])
        """
        n = len(indices)
        if n == 1:
            return [(indices[0], 0)], []

        # find the positions of the free indices and of the dummy indices
        free = [True]*len(indices)
        index_dict = {}
        dum = []
        for i, index in enumerate(indices):
            name = index._name
            typ = index.tensor_index_type
            contr = index._is_up
            if (name, typ) in index_dict:
                # found a pair of dummy indices
                is_contr, pos = index_dict[(name, typ)]
                # check consistency and update free
                if is_contr:
                    if contr:
                        raise ValueError('two equal contravariant indices in slots %d and %d' %(pos, i))
                    else:
                        free[pos] = False
                        free[i] = False
                else:
                    if contr:
                        free[pos] = False
                        free[i] = False
                    else:
                        raise ValueError('two equal covariant indices in slots %d and %d' %(pos, i))
                if contr:
                    dum.append((i, pos))
                else:
                    dum.append((pos, i))
            else:
                index_dict[(name, typ)] = index._is_up, i

        free = [(index, i) for i, index in enumerate(indices) if free[i]]
        free.sort()
        return free, dum

    def get_indices(self):
        """
        Get a list of indices, creating new tensor indices to complete dummy indices.
        """
        return self.indices[:]

    @staticmethod
    def generate_indices_from_free_dum_index_types(free, dum, index_types):
        indices = [None]*(len(free)+2*len(dum))
        for idx, pos in free:
            indices[pos] = idx

        generate_dummy_name = _IndexStructure._get_generator_for_dummy_indices(free)
        for pos1, pos2 in dum:
            typ1 = index_types[pos1]
            indname = generate_dummy_name(typ1)
            indices[pos1] = TensorIndex(indname, typ1, True)
            indices[pos2] = TensorIndex(indname, typ1, False)

        return _IndexStructure._replace_dummy_names(indices, free, dum)

    @staticmethod
    def _get_generator_for_dummy_indices(free):
        cdt = defaultdict(int)
        # if the free indices have names with dummy_fmt, start with an
        # index higher than those for the dummy indices
        # to avoid name collisions
        for indx, ipos in free:
            if indx._name.split('_')[0] == indx.tensor_index_type.dummy_fmt[:-3]:
                cdt[indx.tensor_index_type] = max(cdt[indx.tensor_index_type], int(indx._name.split('_')[1]) + 1)

        def dummy_fmt_gen(tensor_index_type):
            fmt = tensor_index_type.dummy_fmt
            nd = cdt[tensor_index_type]
            cdt[tensor_index_type] += 1
            return fmt % nd

        return dummy_fmt_gen

    @staticmethod
    def _replace_dummy_names(indices, free, dum):
        dum.sort(key=lambda x: x[0])
        new_indices = [ind for ind in indices]
        assert len(indices) == len(free) + 2*len(dum)
        generate_dummy_name = _IndexStructure._get_generator_for_dummy_indices(free)
        for ipos1, ipos2 in dum:
            typ1 = new_indices[ipos1].tensor_index_type
            indname = generate_dummy_name(typ1)
            new_indices[ipos1] = TensorIndex(indname, typ1, True)
            new_indices[ipos2] = TensorIndex(indname, typ1, False)
        return new_indices

    def get_free_indices(self):
        """
        Get a list of free indices.
        """
        # get sorted indices according to their position:
        free = sorted(self.free, key=lambda x: x[1])
        return [i[0] for i in free]

    def __str__(self):
        return "_IndexStructure({0}, {1}, {2})".format(self.free, self.dum, self.index_types)

    def __repr__(self):
        return self.__str__()

    def _get_sorted_free_indices_for_canon(self):
        sorted_free = self.free[:]
        sorted_free.sort(key=lambda x: x[0])
        return sorted_free

    def _get_sorted_dum_indices_for_canon(self):
        return sorted(self.dum, key=lambda x: x[0])

    def _get_lexicographically_sorted_index_types(self):
        permutation = self.indices_canon_args()[0]
        index_types = [None]*self._ext_rank
        for i, it in enumerate(self.index_types):
            index_types[permutation(i)] = it
        return index_types

    def _get_lexicographically_sorted_indices(self):
        permutation = self.indices_canon_args()[0]
        indices = [None]*self._ext_rank
        for i, it in enumerate(self.indices):
            indices[permutation(i)] = it
        return indices

    def perm2tensor(self, g, is_canon_bp=False):
        """
        Returns a ``_IndexStructure`` instance corresponding to the permutation ``g``

        ``g``  permutation corresponding to the tensor in the representation
        used in canonicalization

        ``is_canon_bp``   if True, then ``g`` is the permutation
        corresponding to the canonical form of the tensor
        """
        sorted_free = [i[0] for i in self._get_sorted_free_indices_for_canon()]
        lex_index_types = self._get_lexicographically_sorted_index_types()
        lex_indices = self._get_lexicographically_sorted_indices()
        nfree = len(sorted_free)
        rank = self._ext_rank
        dum = [[None]*2 for i in range((rank - nfree)//2)]
        free = []

        index_types = [None]*rank
        indices = [None]*rank
        for i in range(rank):
            gi = g[i]
            index_types[i] = lex_index_types[gi]
            indices[i] = lex_indices[gi]
            if gi < nfree:
                ind = sorted_free[gi]
                assert index_types[i] == sorted_free[gi].tensor_index_type
                free.append((ind, i))
            else:
                j = gi - nfree
                idum, cov = divmod(j, 2)
                if cov:
                    dum[idum][1] = i
                else:
                    dum[idum][0] = i
        dum = [tuple(x) for x in dum]

        return _IndexStructure(free, dum, index_types, indices)

    def indices_canon_args(self):
        """
        Returns ``(g, dummies, msym, v)``, the entries of ``canonicalize``

        see ``canonicalize`` in ``tensor_can.py``
        """
        # to be called after sorted_components
        from sympy.combinatorics.permutations import _af_new
        n = self._ext_rank
        g = [None]*n + [n, n+1]

        # ordered indices: first the free indices, ordered by types
        # then the dummy indices, ordered by types and contravariant before
        # covariant
        # g[position in tensor] = position in ordered indices
        for i, (indx, ipos) in enumerate(self._get_sorted_free_indices_for_canon()):
            g[ipos] = i
        pos = len(self.free)
        j = len(self.free)
        dummies = []
        prev = None
        a = []
        msym = []
        for ipos1, ipos2 in self._get_sorted_dum_indices_for_canon():
            g[ipos1] = j
            g[ipos2] = j + 1
            j += 2
            typ = self.index_types[ipos1]
            if typ != prev:
                if a:
                    dummies.append(a)
                a = [pos, pos + 1]
                prev = typ
                msym.append(typ.metric_antisym)
            else:
                a.extend([pos, pos + 1])
            pos += 2
        if a:
            dummies.append(a)

        return _af_new(g), dummies, msym


def components_canon_args(components):
    numtyp = []
    prev = None
    for t in components:
        if t == prev:
            numtyp[-1][1] += 1
        else:
            prev = t
            numtyp.append([prev, 1])
    v = []
    for h, n in numtyp:
        if h._comm == 0 or h._comm == 1:
            comm = h._comm
        else:
            comm = TensorManager.get_comm(h._comm, h._comm)
        v.append((h._symmetry.base, h._symmetry.generators, n, comm))
    return v


class _TensorDataLazyEvaluator(CantSympify):
    """
    EXPERIMENTAL: do not rely on this class, it may change without deprecation
    warnings in future versions of SymPy.

    This object contains the logic to associate components data to a tensor
    expression. Components data are set via the ``.data`` property of tensor
    expressions, is stored inside this class as a mapping between the tensor
    expression and the ``ndarray``.

    Computations are executed lazily: whereas the tensor expressions can have
    contractions, tensor products, and additions, components data are not
    computed until they are accessed by reading the ``.data`` property
    associated to the tensor expression.
    """
    _substitutions_dict = dict()
    _substitutions_dict_tensmul = dict()

    def __getitem__(self, key):
        dat = self._get(key)
        if dat is None:
            return None

        from .array import NDimArray
        if not isinstance(dat, NDimArray):
            return dat

        if dat.rank() == 0:
            return dat[()]
        elif dat.rank() == 1 and len(dat) == 1:
            return dat[0]
        return dat

    def _get(self, key):
        """
        Retrieve ``data`` associated with ``key``.

        This algorithm looks into ``self._substitutions_dict`` for all
        ``TensorHead`` in the ``TensExpr`` (or just ``TensorHead`` if key is a
        TensorHead instance). It reconstructs the components data that the
        tensor expression should have by performing on components data the
        operations that correspond to the abstract tensor operations applied.

        Metric tensor is handled in a different manner: it is pre-computed in
        ``self._substitutions_dict_tensmul``.
        """
        if key in self._substitutions_dict:
            return self._substitutions_dict[key]

        if isinstance(key, TensorHead):
            return None

        if isinstance(key, Tensor):
            # special case to handle metrics. Metric tensors cannot be
            # constructed through contraction by the metric, their
            # components show if they are a matrix or its inverse.
            signature = tuple([i.is_up for i in key.get_indices()])
            srch = (key.component,) + signature
            if srch in self._substitutions_dict_tensmul:
                return self._substitutions_dict_tensmul[srch]
            array_list = [self.data_from_tensor(key)]
            return self.data_contract_dum(array_list, key.dum, key.ext_rank)

        if isinstance(key, TensMul):
            tensmul_args = key.args
            if len(tensmul_args) == 1 and len(tensmul_args[0].components) == 1:
                # special case to handle metrics. Metric tensors cannot be
                # constructed through contraction by the metric, their
                # components show if they are a matrix or its inverse.
                signature = tuple([i.is_up for i in tensmul_args[0].get_indices()])
                srch = (tensmul_args[0].components[0],) + signature
                if srch in self._substitutions_dict_tensmul:
                    return self._substitutions_dict_tensmul[srch]
            data_list = [self.data_from_tensor(i) for i in tensmul_args if isinstance(i, TensExpr)]
            coeff = prod([i for i in tensmul_args if not isinstance(i, TensExpr)])
            if all([i is None for i in data_list]):
                return None
            if any([i is None for i in data_list]):
                raise ValueError("Mixing tensors with associated components "\
                                 "data with tensors without components data")
            data_result = self.data_contract_dum(data_list, key.dum, key.ext_rank)
            return coeff*data_result

        if isinstance(key, TensAdd):
            data_list = []
            free_args_list = []
            for arg in key.args:
                if isinstance(arg, TensExpr):
                    data_list.append(arg.data)
                    free_args_list.append([x[0] for x in arg.free])
                else:
                    data_list.append(arg)
                    free_args_list.append([])
            if all([i is None for i in data_list]):
                return None
            if any([i is None for i in data_list]):
                raise ValueError("Mixing tensors with associated components "\
                                 "data with tensors without components data")

            sum_list = []
            from .array import permutedims
            for data, free_args in zip(data_list, free_args_list):
                if len(free_args) < 2:
                    sum_list.append(data)
                else:
                    free_args_pos = {y: x for x, y in enumerate(free_args)}
                    axes = [free_args_pos[arg] for arg in key.free_args]
                    sum_list.append(permutedims(data, axes))
            return reduce(lambda x, y: x+y, sum_list)

        return None

    def data_contract_dum(self, ndarray_list, dum, ext_rank):
        from .array import tensorproduct, tensorcontraction, MutableDenseNDimArray
        arrays = list(map(MutableDenseNDimArray, ndarray_list))
        prodarr = tensorproduct(*arrays)
        return tensorcontraction(prodarr, *dum)

    def data_tensorhead_from_tensmul(self, data, tensmul, tensorhead):
        """
        This method is used when assigning components data to a ``TensMul``
        object, it converts components data to a fully contravariant ndarray,
        which is then stored according to the ``TensorHead`` key.
        """
        if data is None:
            return None

        return self._correct_signature_from_indices(
            data,
            tensmul.get_indices(),
            tensmul.free,
            tensmul.dum,
            True)

    def data_from_tensor(self, tensor):
        """
        This method corrects the components data to the right signature
        (covariant/contravariant) using the metric associated with each
        ``TensorIndexType``.
        """
        tensorhead = tensor.component

        if tensorhead.data is None:
            return None

        return self._correct_signature_from_indices(
            tensorhead.data,
            tensor.get_indices(),
            tensor.free,
            tensor.dum)

    def _assign_data_to_tensor_expr(self, key, data):
        if isinstance(key, TensAdd):
            raise ValueError('cannot assign data to TensAdd')
        # here it is assumed that `key` is a `TensMul` instance.
        if len(key.components) != 1:
            raise ValueError('cannot assign data to TensMul with multiple components')
        tensorhead = key.components[0]
        newdata = self.data_tensorhead_from_tensmul(data, key, tensorhead)
        return tensorhead, newdata

    def _check_permutations_on_data(self, tens, data):
        from .array import permutedims

        if isinstance(tens, TensorHead):
            rank = tens.rank
            generators = tens.symmetry.generators
        elif isinstance(tens, Tensor):
            rank = tens.rank
            generators = tens.components[0].symmetry.generators
        elif isinstance(tens, TensorIndexType):
            rank = tens.metric.rank
            generators = tens.metric.symmetry.generators

        # Every generator is a permutation, check that by permuting the array
        # by that permutation, the array will be the same, except for a
        # possible sign change if the permutation admits it.
        for gener in generators:
            sign_change = +1 if (gener(rank) == rank) else -1
            data_swapped = data
            last_data = data
            permute_axes = list(map(gener, list(range(rank))))
            # the order of a permutation is the number of times to get the
            # identity by applying that permutation.
            for i in range(gener.order()-1):
                data_swapped = permutedims(data_swapped, permute_axes)
                # if any value in the difference array is non-zero, raise an error:
                if any(last_data - sign_change*data_swapped):
                    raise ValueError("Component data symmetry structure error")
                last_data = data_swapped

    def __setitem__(self, key, value):
        """
        Set the components data of a tensor object/expression.

        Components data are transformed to the all-contravariant form and stored
        with the corresponding ``TensorHead`` object. If a ``TensorHead`` object
        cannot be uniquely identified, it will raise an error.
        """
        data = _TensorDataLazyEvaluator.parse_data(value)
        self._check_permutations_on_data(key, data)

        # TensorHead and TensorIndexType can be assigned data directly, while
        # TensMul must first convert data to a fully contravariant form, and
        # assign it to its corresponding TensorHead single component.
        if not isinstance(key, (TensorHead, TensorIndexType)):
            key, data = self._assign_data_to_tensor_expr(key, data)

        if isinstance(key, TensorHead):
            for dim, indextype in zip(data.shape, key.index_types):
                if indextype.data is None:
                    raise ValueError("index type {} has no components data"\
                    " associated (needed to raise/lower index)".format(indextype))
                if indextype.dim is None:
                    continue
                if dim != indextype.dim:
                    raise ValueError("wrong dimension of ndarray")
        self._substitutions_dict[key] = data

    def __delitem__(self, key):
        del self._substitutions_dict[key]

    def __contains__(self, key):
        return key in self._substitutions_dict

    def add_metric_data(self, metric, data):
        """
        Assign data to the ``metric`` tensor. The metric tensor behaves in an
        anomalous way when raising and lowering indices.

        A fully covariant metric is the inverse transpose of the fully
        contravariant metric (it is meant matrix inverse). If the metric is
        symmetric, the transpose is not necessary and mixed
        covariant/contravariant metrics are Kronecker deltas.
        """
        # hard assignment, data should not be added to `TensorHead` for metric:
        # the problem with `TensorHead` is that the metric is anomalous, i.e.
        # raising and lowering the index means considering the metric or its
        # inverse, this is not the case for other tensors.
        self._substitutions_dict_tensmul[metric, True, True] = data
        inverse_transpose = self.inverse_transpose_matrix(data)
        # in symmetric spaces, the traspose is the same as the original matrix,
        # the full covariant metric tensor is the inverse transpose, so this
        # code will be able to handle non-symmetric metrics.
        self._substitutions_dict_tensmul[metric, False, False] = inverse_transpose
        # now mixed cases, these are identical to the unit matrix if the metric
        # is symmetric.
        m = data.tomatrix()
        invt = inverse_transpose.tomatrix()
        self._substitutions_dict_tensmul[metric, True, False] = m * invt
        self._substitutions_dict_tensmul[metric, False, True] = invt * m

    @staticmethod
    def _flip_index_by_metric(data, metric, pos):
        from .array import tensorproduct, tensorcontraction, permutedims, MutableDenseNDimArray, NDimArray

        mdim = metric.rank()
        ddim = data.rank()

        if pos == 0:
            data = tensorcontraction(
                tensorproduct(
                    metric,
                    data
                ),
                (1, mdim+pos)
            )
        else:
            data = tensorcontraction(
                tensorproduct(
                    data,
                    metric
                ),
                (pos, ddim)
            )
        return data

    @staticmethod
    def inverse_matrix(ndarray):
        m = ndarray.tomatrix().inv()
        return _TensorDataLazyEvaluator.parse_data(m)

    @staticmethod
    def inverse_transpose_matrix(ndarray):
        m = ndarray.tomatrix().inv().T
        return _TensorDataLazyEvaluator.parse_data(m)

    @staticmethod
    def _correct_signature_from_indices(data, indices, free, dum, inverse=False):
        """
        Utility function to correct the values inside the components data
        ndarray according to whether indices are covariant or contravariant.

        It uses the metric matrix to lower values of covariant indices.
        """
        # change the ndarray values according covariantness/contravariantness of the indices
        # use the metric
        for i, indx in enumerate(indices):
            if not indx.is_up and not inverse:
                data = _TensorDataLazyEvaluator._flip_index_by_metric(data, indx.tensor_index_type.data, i)
            elif not indx.is_up and inverse:
                data = _TensorDataLazyEvaluator._flip_index_by_metric(
                    data,
                    _TensorDataLazyEvaluator.inverse_matrix(indx.tensor_index_type.data),
                    i
                )
        return data

    @staticmethod
    def _sort_data_axes(old, new):
        from .array import permutedims

        new_data = old.data.copy()

        old_free = [i[0] for i in old.free]
        new_free = [i[0] for i in new.free]

        for i in range(len(new_free)):
            for j in range(i, len(old_free)):
                if old_free[j] == new_free[i]:
                    old_free[i], old_free[j] = old_free[j], old_free[i]
                    new_data = permutedims(new_data, (i, j))
                    break
        return new_data

    @staticmethod
    def add_rearrange_tensmul_parts(new_tensmul, old_tensmul):
        def sorted_compo():
            return _TensorDataLazyEvaluator._sort_data_axes(old_tensmul, new_tensmul)

        _TensorDataLazyEvaluator._substitutions_dict[new_tensmul] = sorted_compo()

    @staticmethod
    def parse_data(data):
        """
        Transform ``data`` to array. The parameter ``data`` may
        contain data in various formats, e.g. nested lists, sympy ``Matrix``,
        and so on.

        Examples
        ========

        >>> from sympy.tensor.tensor import _TensorDataLazyEvaluator
        >>> _TensorDataLazyEvaluator.parse_data([1, 3, -6, 12])
        [1, 3, -6, 12]

        >>> _TensorDataLazyEvaluator.parse_data([[1, 2], [4, 7]])
        [[1, 2], [4, 7]]
        """
        from .array import MutableDenseNDimArray

        if not isinstance(data, MutableDenseNDimArray):
            if len(data) == 2 and hasattr(data[0], '__call__'):
                data = MutableDenseNDimArray(data[0], data[1])
            else:
                data = MutableDenseNDimArray(data)
        return data

_tensor_data_substitution_dict = _TensorDataLazyEvaluator()


class _TensorManager(object):
    """
    Class to manage tensor properties.

    Notes
    =====

    Tensors belong to tensor commutation groups; each group has a label
    ``comm``; there are predefined labels:

    ``0``   tensors commuting with any other tensor

    ``1``   tensors anticommuting among themselves

    ``2``   tensors not commuting, apart with those with ``comm=0``

    Other groups can be defined using ``set_comm``; tensors in those
    groups commute with those with ``comm=0``; by default they
    do not commute with any other group.
    """
    def __init__(self):
        self._comm_init()

    def _comm_init(self):
        self._comm = [{} for i in range(3)]
        for i in range(3):
            self._comm[0][i] = 0
            self._comm[i][0] = 0
        self._comm[1][1] = 1
        self._comm[2][1] = None
        self._comm[1][2] = None
        self._comm_symbols2i = {0:0, 1:1, 2:2}
        self._comm_i2symbol = {0:0, 1:1, 2:2}

    @property
    def comm(self):
        return self._comm

    def comm_symbols2i(self, i):
        """
        get the commutation group number corresponding to ``i``

        ``i`` can be a symbol or a number or a string

        If ``i`` is not already defined its commutation group number
        is set.
        """
        if i not in self._comm_symbols2i:
            n = len(self._comm)
            self._comm.append({})
            self._comm[n][0] = 0
            self._comm[0][n] = 0
            self._comm_symbols2i[i] = n
            self._comm_i2symbol[n] = i
            return n
        return self._comm_symbols2i[i]

    def comm_i2symbol(self, i):
        """
        Returns the symbol corresponding to the commutation group number.
        """
        return self._comm_i2symbol[i]

    def set_comm(self, i, j, c):
        """
        set the commutation parameter ``c`` for commutation groups ``i, j``

        Parameters
        ==========

        i, j : symbols representing commutation groups

        c  :  group commutation number

        Notes
        =====

        ``i, j`` can be symbols, strings or numbers,
        apart from ``0, 1`` and ``2`` which are reserved respectively
        for commuting, anticommuting tensors and tensors not commuting
        with any other group apart with the commuting tensors.
        For the remaining cases, use this method to set the commutation rules;
        by default ``c=None``.

        The group commutation number ``c`` is assigned in correspondence
        to the group commutation symbols; it can be

        0        commuting

        1        anticommuting

        None     no commutation property

        Examples
        ========

        ``G`` and ``GH`` do not commute with themselves and commute with
        each other; A is commuting.

        >>> from sympy.tensor.tensor import TensorIndexType, tensor_indices, tensorhead, TensorManager
        >>> Lorentz = TensorIndexType('Lorentz')
        >>> i0,i1,i2,i3,i4 = tensor_indices('i0:5', Lorentz)
        >>> A = tensorhead('A', [Lorentz], [[1]])
        >>> G = tensorhead('G', [Lorentz], [[1]], 'Gcomm')
        >>> GH = tensorhead('GH', [Lorentz], [[1]], 'GHcomm')
        >>> TensorManager.set_comm('Gcomm', 'GHcomm', 0)
        >>> (GH(i1)*G(i0)).canon_bp()
        G(i0)*GH(i1)
        >>> (G(i1)*G(i0)).canon_bp()
        G(i1)*G(i0)
        >>> (G(i1)*A(i0)).canon_bp()
        A(i0)*G(i1)
        """
        if c not in (0, 1, None):
            raise ValueError('`c` can assume only the values 0, 1 or None')

        if i not in self._comm_symbols2i:
            n = len(self._comm)
            self._comm.append({})
            self._comm[n][0] = 0
            self._comm[0][n] = 0
            self._comm_symbols2i[i] = n
            self._comm_i2symbol[n] = i
        if j not in self._comm_symbols2i:
            n = len(self._comm)
            self._comm.append({})
            self._comm[0][n] = 0
            self._comm[n][0] = 0
            self._comm_symbols2i[j] = n
            self._comm_i2symbol[n] = j
        ni = self._comm_symbols2i[i]
        nj = self._comm_symbols2i[j]
        self._comm[ni][nj] = c
        self._comm[nj][ni] = c

    def set_comms(self, *args):
        """
        set the commutation group numbers ``c`` for symbols ``i, j``

        Parameters
        ==========

        args : sequence of ``(i, j, c)``
        """
        for i, j, c in args:
            self.set_comm(i, j, c)

    def get_comm(self, i, j):
        """
        Return the commutation parameter for commutation group numbers ``i, j``

        see ``_TensorManager.set_comm``
        """
        return self._comm[i].get(j, 0 if i == 0 or j == 0 else None)

    def clear(self):
        """
        Clear the TensorManager.
        """
        self._comm_init()


TensorManager = _TensorManager()


class TensorIndexType(Basic):
    """
    A TensorIndexType is characterized by its name and its metric.

    Parameters
    ==========

    name : name of the tensor type

    metric : metric symmetry or metric object or ``None``


    dim : dimension, it can be a symbol or an integer or ``None``

    eps_dim : dimension of the epsilon tensor

    dummy_fmt : name of the head of dummy indices

    Attributes
    ==========

    ``name``
    ``metric_name`` : it is 'metric' or metric.name
    ``metric_antisym``
    ``metric`` : the metric tensor
    ``delta`` : ``Kronecker delta``
    ``epsilon`` : the ``Levi-Civita epsilon`` tensor
    ``dim``
    ``eps_dim``
    ``dummy_fmt``
    ``data`` : a property to add ``ndarray`` values, to work in a specified basis.

    Notes
    =====

    The ``metric`` parameter can be:
    ``metric = False`` symmetric metric (in Riemannian geometry)

    ``metric = True`` antisymmetric metric (for spinor calculus)

    ``metric = None``  there is no metric

    ``metric`` can be an object having ``name`` and ``antisym`` attributes.


    If there is a metric the metric is used to raise and lower indices.

    In the case of antisymmetric metric, the following raising and
    lowering conventions will be adopted:

    ``psi(a) = g(a, b)*psi(-b); chi(-a) = chi(b)*g(-b, -a)``

    ``g(-a, b) = delta(-a, b); g(b, -a) = -delta(a, -b)``

    where ``delta(-a, b) = delta(b, -a)`` is the ``Kronecker delta``
    (see ``TensorIndex`` for the conventions on indices).

    If there is no metric it is not possible to raise or lower indices;
    e.g. the index of the defining representation of ``SU(N)``
    is 'covariant' and the conjugate representation is
    'contravariant'; for ``N > 2`` they are linearly independent.

    ``eps_dim`` is by default equal to ``dim``, if the latter is an integer;
    else it can be assigned (for use in naive dimensional regularization);
    if ``eps_dim`` is not an integer ``epsilon`` is ``None``.

    Examples
    ========

    >>> from sympy.tensor.tensor import TensorIndexType
    >>> Lorentz = TensorIndexType('Lorentz', dummy_fmt='L')
    >>> Lorentz.metric
    metric(Lorentz,Lorentz)

    Examples with metric components data added, this means it is working on a
    fixed basis:

    >>> Lorentz.data = [1, -1, -1, -1]
    >>> Lorentz
    TensorIndexType(Lorentz, 0)
    >>> Lorentz.data
    [[1, 0, 0, 0], [0, -1, 0, 0], [0, 0, -1, 0], [0, 0, 0, -1]]
    """

    def __new__(cls, name, metric=False, dim=None, eps_dim=None,
                dummy_fmt=None):

        if isinstance(name, string_types):
            name = Symbol(name)
        obj = Basic.__new__(cls, name, S.One if metric else S.Zero)
        obj._name = str(name)
        if not dummy_fmt:
            obj._dummy_fmt = '%s_%%d' % obj.name
        else:
            obj._dummy_fmt = '%s_%%d' % dummy_fmt
        if metric is None:
            obj.metric_antisym = None
            obj.metric = None
        else:
            if metric in (True, False, 0, 1):
                metric_name = 'metric'
                obj.metric_antisym = metric
            else:
                metric_name = metric.name
                obj.metric_antisym = metric.antisym
            sym2 = TensorSymmetry(get_symmetric_group_sgs(2, obj.metric_antisym))
            S2 = TensorType([obj]*2, sym2)
            obj.metric = S2(metric_name)

        obj._dim = dim
        obj._delta = obj.get_kronecker_delta()
        obj._eps_dim = eps_dim if eps_dim else dim
        obj._epsilon = obj.get_epsilon()
        obj._autogenerated = []
        return obj

    @property
    @deprecated(useinstead="TensorIndex", issue=12857, deprecated_since_version="1.1")
    def auto_right(self):
        if not hasattr(self, '_auto_right'):
            self._auto_right = TensorIndex("auto_right", self)
        return self._auto_right

    @property
    @deprecated(useinstead="TensorIndex", issue=12857, deprecated_since_version="1.1")
    def auto_left(self):
        if not hasattr(self, '_auto_left'):
            self._auto_left = TensorIndex("auto_left", self)
        return self._auto_left

    @property
    @deprecated(useinstead="TensorIndex", issue=12857, deprecated_since_version="1.1")
    def auto_index(self):
        if not hasattr(self, '_auto_index'):
            self._auto_index = TensorIndex("auto_index", self)
        return self._auto_index

    @property
    def data(self):
        return _tensor_data_substitution_dict[self]

    @data.setter
    def data(self, data):
        # This assignment is a bit controversial, should metric components be assigned
        # to the metric only or also to the TensorIndexType object? The advantage here
        # is the ability to assign a 1D array and transform it to a 2D diagonal array.
        from .array import MutableDenseNDimArray

        data = _TensorDataLazyEvaluator.parse_data(data)
        if data.rank() > 2:
            raise ValueError("data have to be of rank 1 (diagonal metric) or 2.")
        if data.rank() == 1:
            if self.dim is not None:
                nda_dim = data.shape[0]
                if nda_dim != self.dim:
                    raise ValueError("Dimension mismatch")

            dim = data.shape[0]
            newndarray = MutableDenseNDimArray.zeros(dim, dim)
            for i, val in enumerate(data):
                newndarray[i, i] = val
            data = newndarray
        dim1, dim2 = data.shape
        if dim1 != dim2:
            raise ValueError("Non-square matrix tensor.")
        if self.dim is not None:
            if self.dim != dim1:
                raise ValueError("Dimension mismatch")
        _tensor_data_substitution_dict[self] = data
        _tensor_data_substitution_dict.add_metric_data(self.metric, data)
        delta = self.get_kronecker_delta()
        i1 = TensorIndex('i1', self)
        i2 = TensorIndex('i2', self)
        delta(i1, -i2).data = _TensorDataLazyEvaluator.parse_data(eye(dim1))

    @data.deleter
    def data(self):
        if self in _tensor_data_substitution_dict:
            del _tensor_data_substitution_dict[self]
        if self.metric in _tensor_data_substitution_dict:
            del _tensor_data_substitution_dict[self.metric]

    def _get_matrix_fmt(self, number):
        return ("m" + self.dummy_fmt) % (number)

    @property
    def name(self):
        return self._name

    @property
    def dim(self):
        return self._dim

    @property
    def delta(self):
        return self._delta

    @property
    def eps_dim(self):
        return self._eps_dim

    @property
    def epsilon(self):
        return self._epsilon

    @property
    def dummy_fmt(self):
        return self._dummy_fmt

    def get_kronecker_delta(self):
        sym2 = TensorSymmetry(get_symmetric_group_sgs(2))
        S2 = TensorType([self]*2, sym2)
        delta = S2('KD')
        return delta

    def get_epsilon(self):
        if not isinstance(self._eps_dim, (SYMPY_INTS, Integer)):
            return None
        sym = TensorSymmetry(get_symmetric_group_sgs(self._eps_dim, 1))
        Sdim = TensorType([self]*self._eps_dim, sym)
        epsilon = Sdim('Eps')
        return epsilon

    def __lt__(self, other):
        return self.name < other.name

    def __str__(self):
        return self.name

    __repr__ = __str__

    def _components_data_full_destroy(self):
        """
        EXPERIMENTAL: do not rely on this API method.

        This destroys components data associated to the ``TensorIndexType``, if
        any, specifically:

        * metric tensor data
        * Kronecker tensor data
        """
        if self in _tensor_data_substitution_dict:
            del _tensor_data_substitution_dict[self]

        def delete_tensmul_data(key):
            if key in _tensor_data_substitution_dict._substitutions_dict_tensmul:
                del _tensor_data_substitution_dict._substitutions_dict_tensmul[key]

        # delete metric data:
        delete_tensmul_data((self.metric, True, True))
        delete_tensmul_data((self.metric, True, False))
        delete_tensmul_data((self.metric, False, True))
        delete_tensmul_data((self.metric, False, False))

        # delete delta tensor data:
        delta = self.get_kronecker_delta()
        if delta in _tensor_data_substitution_dict:
            del _tensor_data_substitution_dict[delta]


class TensorIndex(Basic):
    """
    Represents an abstract tensor index.

    Parameters
    ==========

    name : name of the index, or ``True`` if you want it to be automatically assigned
    tensortype : ``TensorIndexType`` of the index
    is_up :  flag for contravariant index

    Attributes
    ==========

    ``name``
    ``tensortype``
    ``is_up``

    Notes
    =====

    Tensor indices are contracted with the Einstein summation convention.

    An index can be in contravariant or in covariant form; in the latter
    case it is represented prepending a ``-`` to the index name.

    Dummy indices have a name with head given by ``tensortype._dummy_fmt``


    Examples
    ========

    >>> from sympy.tensor.tensor import TensorIndexType, TensorIndex, TensorSymmetry, TensorType, get_symmetric_group_sgs
    >>> Lorentz = TensorIndexType('Lorentz', dummy_fmt='L')
    >>> i = TensorIndex('i', Lorentz); i
    i
    >>> sym1 = TensorSymmetry(*get_symmetric_group_sgs(1))
    >>> S1 = TensorType([Lorentz], sym1)
    >>> A, B = S1('A,B')
    >>> A(i)*B(-i)
    A(L_0)*B(-L_0)

    If you want the index name to be automatically assigned, just put ``True``
    in the ``name`` field, it will be generated using the reserved character
    ``_`` in front of its name, in order to avoid conflicts with possible
    existing indices:

    >>> i0 = TensorIndex(True, Lorentz)
    >>> i0
    _i0
    >>> i1 = TensorIndex(True, Lorentz)
    >>> i1
    _i1
    >>> A(i0)*B(-i1)
    A(_i0)*B(-_i1)
    >>> A(i0)*B(-i0)
    A(L_0)*B(-L_0)
    """
    def __new__(cls, name, tensortype, is_up=True):
        if isinstance(name, string_types):
            name_symbol = Symbol(name)
        elif isinstance(name, Symbol):
            name_symbol = name
        elif name is True:
            name = "_i{0}".format(len(tensortype._autogenerated))
            name_symbol = Symbol(name)
            tensortype._autogenerated.append(name_symbol)
        else:
            raise ValueError("invalid name")

        is_up = sympify(is_up)
        obj = Basic.__new__(cls, name_symbol, tensortype, is_up)
        obj._name = str(name)
        obj._tensor_index_type = tensortype
        obj._is_up = is_up
        return obj

    @property
    def name(self):
        return self._name

    @property
    @deprecated(useinstead="tensor_index_type", issue=12857, deprecated_since_version="1.1")
    def tensortype(self):
        return self.tensor_index_type

    @property
    def tensor_index_type(self):
        return self._tensor_index_type

    @property
    def is_up(self):
        return self._is_up

    def _print(self):
        s = self._name
        if not self._is_up:
            s = '-%s' % s
        return s

    def __lt__(self, other):
        return (self.tensor_index_type, self._name) < (other.tensor_index_type, other._name)

    def __neg__(self):
        t1 = TensorIndex(self.name, self.tensor_index_type,
                (not self.is_up))
        return t1


def tensor_indices(s, typ):
    """
    Returns list of tensor indices given their names and their types

    Parameters
    ==========

    s : string of comma separated names of indices

    typ : ``TensorIndexType`` of the indices

    Examples
    ========

    >>> from sympy.tensor.tensor import TensorIndexType, tensor_indices
    >>> Lorentz = TensorIndexType('Lorentz', dummy_fmt='L')
    >>> a, b, c, d = tensor_indices('a,b,c,d', Lorentz)
    """
    if isinstance(s, str):
        a = [x.name for x in symbols(s, seq=True)]
    else:
        raise ValueError('expecting a string')

    tilist = [TensorIndex(i, typ) for i in a]
    if len(tilist) == 1:
        return tilist[0]
    return tilist


class TensorSymmetry(Basic):
    """
    Monoterm symmetry of a tensor

    Parameters
    ==========

    bsgs : tuple ``(base, sgs)`` BSGS of the symmetry of the tensor

    Attributes
    ==========

    ``base`` : base of the BSGS
    ``generators`` : generators of the BSGS
    ``rank`` : rank of the tensor

    Notes
    =====

    A tensor can have an arbitrary monoterm symmetry provided by its BSGS.
    Multiterm symmetries, like the cyclic symmetry of the Riemann tensor,
    are not covered.

    See Also
    ========

    sympy.combinatorics.tensor_can.get_symmetric_group_sgs

    Examples
    ========

    Define a symmetric tensor

    >>> from sympy.tensor.tensor import TensorIndexType, TensorSymmetry, TensorType, get_symmetric_group_sgs
    >>> Lorentz = TensorIndexType('Lorentz', dummy_fmt='L')
    >>> sym2 = TensorSymmetry(get_symmetric_group_sgs(2))
    >>> S2 = TensorType([Lorentz]*2, sym2)
    >>> V = S2('V')
    """
    def __new__(cls, *args, **kw_args):
        if len(args) == 1:
            base, generators = args[0]
        elif len(args) == 2:
            base, generators = args
        else:
            raise TypeError("bsgs required, either two separate parameters or one tuple")

        if not isinstance(base, Tuple):
            base = Tuple(*base)
        if not isinstance(generators, Tuple):
            generators = Tuple(*generators)
        obj = Basic.__new__(cls, base, generators, **kw_args)
        return obj

    @property
    def base(self):
        return self.args[0]

    @property
    def generators(self):
        return self.args[1]

    @property
    def rank(self):
        return self.args[1][0].size - 2


def tensorsymmetry(*args):
    """
    Return a ``TensorSymmetry`` object.

    One can represent a tensor with any monoterm slot symmetry group
    using a BSGS.

    ``args`` can be a BSGS
    ``args[0]``    base
    ``args[1]``    sgs

    Usually tensors are in (direct products of) representations
    of the symmetric group;
    ``args`` can be a list of lists representing the shapes of Young tableaux

    Notes
    =====

    For instance:
    ``[[1]]``       vector
    ``[[1]*n]``     symmetric tensor of rank ``n``
    ``[[n]]``       antisymmetric tensor of rank ``n``
    ``[[2, 2]]``    monoterm slot symmetry of the Riemann tensor
    ``[[1],[1]]``   vector*vector
    ``[[2],[1],[1]`` (antisymmetric tensor)*vector*vector

    Notice that with the shape ``[2, 2]`` we associate only the monoterm
    symmetries of the Riemann tensor; this is an abuse of notation,
    since the shape ``[2, 2]`` corresponds usually to the irreducible
    representation characterized by the monoterm symmetries and by the
    cyclic symmetry.

    Examples
    ========

    Symmetric tensor using a Young tableau

    >>> from sympy.tensor.tensor import TensorIndexType, TensorType, tensorsymmetry
    >>> Lorentz = TensorIndexType('Lorentz', dummy_fmt='L')
    >>> sym2 = tensorsymmetry([1, 1])
    >>> S2 = TensorType([Lorentz]*2, sym2)
    >>> V = S2('V')

    Symmetric tensor using a ``BSGS`` (base, strong generator set)

    >>> from sympy.tensor.tensor import get_symmetric_group_sgs
    >>> sym2 = tensorsymmetry(*get_symmetric_group_sgs(2))
    >>> S2 = TensorType([Lorentz]*2, sym2)
    >>> V = S2('V')
    """
    from sympy.combinatorics import Permutation

    def tableau2bsgs(a):
        if len(a) == 1:
            # antisymmetric vector
            n = a[0]
            bsgs = get_symmetric_group_sgs(n, 1)
        else:
            if all(x == 1 for x in a):
                # symmetric vector
                n = len(a)
                bsgs = get_symmetric_group_sgs(n)
            elif a == [2, 2]:
                bsgs = riemann_bsgs
            else:
                raise NotImplementedError
        return bsgs

    if not args:
        return TensorSymmetry(Tuple(), Tuple(Permutation(1)))

    if len(args) == 2 and isinstance(args[1][0], Permutation):
        return TensorSymmetry(args)
    base, sgs = tableau2bsgs(args[0])
    for a in args[1:]:
        basex, sgsx = tableau2bsgs(a)
        base, sgs = bsgs_direct_product(base, sgs, basex, sgsx)
    return TensorSymmetry(Tuple(base, sgs))


class TensorType(Basic):
    """
    Class of tensor types.

    Parameters
    ==========

    index_types : list of ``TensorIndexType`` of the tensor indices
    symmetry : ``TensorSymmetry`` of the tensor

    Attributes
    ==========

    ``index_types``
    ``symmetry``
    ``types`` : list of ``TensorIndexType`` without repetitions

    Examples
    ========

    Define a symmetric tensor

    >>> from sympy.tensor.tensor import TensorIndexType, tensorsymmetry, TensorType
    >>> Lorentz = TensorIndexType('Lorentz', dummy_fmt='L')
    >>> sym2 = tensorsymmetry([1, 1])
    >>> S2 = TensorType([Lorentz]*2, sym2)
    >>> V = S2('V')
    """
    is_commutative = False

    def __new__(cls, index_types, symmetry, **kw_args):
        assert symmetry.rank == len(index_types)
        obj = Basic.__new__(cls, Tuple(*index_types), symmetry, **kw_args)
        return obj

    @property
    def index_types(self):
        return self.args[0]

    @property
    def symmetry(self):
        return self.args[1]

    @property
    def types(self):
        return sorted(set(self.index_types), key=lambda x: x.name)

    def __str__(self):
        return 'TensorType(%s)' % ([str(x) for x in self.index_types])

    def __call__(self, s, comm=0):
        """
        Return a TensorHead object or a list of TensorHead objects.

        ``s``  name or string of names

        ``comm``: commutation group number
        see ``_TensorManager.set_comm``

        Examples
        ========

        Define symmetric tensors ``V``, ``W`` and ``G``, respectively
        commuting, anticommuting and with no commutation symmetry

        >>> from sympy.tensor.tensor import TensorIndexType, tensor_indices, tensorsymmetry, TensorType, canon_bp
        >>> Lorentz = TensorIndexType('Lorentz', dummy_fmt='L')
        >>> a, b = tensor_indices('a,b', Lorentz)
        >>> sym2 = tensorsymmetry([1]*2)
        >>> S2 = TensorType([Lorentz]*2, sym2)
        >>> V = S2('V')
        >>> W = S2('W', 1)
        >>> G = S2('G', 2)
        >>> canon_bp(V(a, b)*V(-b, -a))
        V(L_0, L_1)*V(-L_0, -L_1)
        >>> canon_bp(W(a, b)*W(-b, -a))
        0
        """
        if isinstance(s, str):
            names = [x.name for x in symbols(s, seq=True)]
        else:
            raise ValueError('expecting a string')
        if len(names) == 1:
            return TensorHead(names[0], self, comm)
        else:
            return [TensorHead(name, self, comm) for name in names]


def tensorhead(name, typ, sym, comm=0):
    """
    Function generating tensorhead(s).

    Parameters
    ==========

    name : name or sequence of names (as in ``symbol``)

    typ :  index types

    sym :  same as ``*args`` in ``tensorsymmetry``

    comm : commutation group number
    see ``_TensorManager.set_comm``


    Examples
    ========

    >>> from sympy.tensor.tensor import TensorIndexType, tensor_indices, tensorhead
    >>> Lorentz = TensorIndexType('Lorentz', dummy_fmt='L')
    >>> a, b = tensor_indices('a,b', Lorentz)
    >>> A = tensorhead('A', [Lorentz]*2, [[1]*2])
    >>> A(a, -b)
    A(a, -b)

    """
    sym = tensorsymmetry(*sym)
    S = TensorType(typ, sym)
    th = S(name, comm)
    return th


class TensorHead(Basic):
    r"""
    Tensor head of the tensor

    Parameters
    ==========

    name : name of the tensor

    typ : list of TensorIndexType

    comm : commutation group number

    Attributes
    ==========

    ``name``
    ``index_types``
    ``rank``
    ``types``  :  equal to ``typ.types``
    ``symmetry`` : equal to ``typ.symmetry``
    ``comm`` : commutation group

    Notes
    =====

    A ``TensorHead`` belongs to a commutation group, defined by a
    symbol on number ``comm`` (see ``_TensorManager.set_comm``);
    tensors in a commutation group have the same commutation properties;
    by default ``comm`` is ``0``, the group of the commuting tensors.

    Examples
    ========

    >>> from sympy.tensor.tensor import TensorIndexType, tensorhead, TensorType
    >>> Lorentz = TensorIndexType('Lorentz', dummy_fmt='L')
    >>> A = tensorhead('A', [Lorentz, Lorentz], [[1],[1]])

    Examples with ndarray values, the components data assigned to the
    ``TensorHead`` object are assumed to be in a fully-contravariant
    representation. In case it is necessary to assign components data which
    represents the values of a non-fully covariant tensor, see the other
    examples.

    >>> from sympy.tensor.tensor import tensor_indices, tensorhead
    >>> Lorentz.data = [1, -1, -1, -1]
    >>> i0, i1 = tensor_indices('i0:2', Lorentz)
    >>> A.data = [[j+2*i for j in range(4)] for i in range(4)]

    in order to retrieve data, it is also necessary to specify abstract indices
    enclosed by round brackets, then numerical indices inside square brackets.

    >>> A(i0, i1)[0, 0]
    0
    >>> A(i0, i1)[2, 3] == 3+2*2
    True

    Notice that square brackets create a valued tensor expression instance:

    >>> A(i0, i1)
    A(i0, i1)

    To view the data, just type:

    >>> A.data
    [[0, 1, 2, 3], [2, 3, 4, 5], [4, 5, 6, 7], [6, 7, 8, 9]]

    Turning to a tensor expression, covariant indices get the corresponding
    components data corrected by the metric:

    >>> A(i0, -i1).data
    [[0, -1, -2, -3], [2, -3, -4, -5], [4, -5, -6, -7], [6, -7, -8, -9]]

    >>> A(-i0, -i1).data
    [[0, -1, -2, -3], [-2, 3, 4, 5], [-4, 5, 6, 7], [-6, 7, 8, 9]]

    while if all indices are contravariant, the ``ndarray`` remains the same

    >>> A(i0, i1).data
    [[0, 1, 2, 3], [2, 3, 4, 5], [4, 5, 6, 7], [6, 7, 8, 9]]

    When all indices are contracted and components data are added to the tensor,
    accessing the data will return a scalar, no array object. In fact, arrays
    are dropped to scalars if they contain only one element.

    >>> A(i0, -i0)
    A(L_0, -L_0)
    >>> A(i0, -i0).data
    -18

    It is also possible to assign components data to an indexed tensor, i.e. a
    tensor with specified covariant and contravariant components. In this
    example, the covariant components data of the Electromagnetic tensor are
    injected into `A`:

    >>> from sympy import symbols
    >>> Ex, Ey, Ez, Bx, By, Bz = symbols('E_x E_y E_z B_x B_y B_z')
    >>> c = symbols('c', positive=True)

    Let's define `F`, an antisymmetric tensor, we have to assign an
    antisymmetric matrix to it, because `[[2]]` stands for the Young tableau
    representation of an antisymmetric set of two elements:

    >>> F = tensorhead('A', [Lorentz, Lorentz], [[2]])
    >>> F(-i0, -i1).data = [
    ... [0, Ex/c, Ey/c, Ez/c],
    ... [-Ex/c, 0, -Bz, By],
    ... [-Ey/c, Bz, 0, -Bx],
    ... [-Ez/c, -By, Bx, 0]]

    Now it is possible to retrieve the contravariant form of the Electromagnetic
    tensor:

    >>> F(i0, i1).data
    [[0, -E_x/c, -E_y/c, -E_z/c], [E_x/c, 0, -B_z, B_y], [E_y/c, B_z, 0, -B_x], [E_z/c, -B_y, B_x, 0]]

    and the mixed contravariant-covariant form:

    >>> F(i0, -i1).data
    [[0, E_x/c, E_y/c, E_z/c], [E_x/c, 0, B_z, -B_y], [E_y/c, -B_z, 0, B_x], [E_z/c, B_y, -B_x, 0]]

    To convert the darray to a SymPy matrix, just cast:

    >>> F.data.tomatrix()
    Matrix([
    [    0, -E_x/c, -E_y/c, -E_z/c],
    [E_x/c,      0,   -B_z,    B_y],
    [E_y/c,    B_z,      0,   -B_x],
    [E_z/c,   -B_y,    B_x,      0]])

    Still notice, in this last example, that accessing components data from a
    tensor without specifying the indices is equivalent to assume that all
    indices are contravariant.

    It is also possible to store symbolic components data inside a tensor, for
    example, define a four-momentum-like tensor:

    >>> from sympy import symbols
    >>> P = tensorhead('P', [Lorentz], [[1]])
    >>> E, px, py, pz = symbols('E p_x p_y p_z', positive=True)
    >>> P.data = [E, px, py, pz]

    The contravariant and covariant components are, respectively:

    >>> P(i0).data
    [E, p_x, p_y, p_z]
    >>> P(-i0).data
    [E, -p_x, -p_y, -p_z]

    The contraction of a 1-index tensor by itself is usually indicated by a
    power by two:

    >>> P(i0)**2
    E**2 - p_x**2 - p_y**2 - p_z**2

    As the power by two is clearly identical to `P_\mu P^\mu`, it is possible to
    simply contract the ``TensorHead`` object, without specifying the indices

    >>> P**2
    E**2 - p_x**2 - p_y**2 - p_z**2
    """
    is_commutative = False

    def __new__(cls, name, typ, comm=0, **kw_args):
        if isinstance(name, string_types):
            name_symbol = Symbol(name)
        elif isinstance(name, Symbol):
            name_symbol = name
        else:
            raise ValueError("invalid name")

        comm2i = TensorManager.comm_symbols2i(comm)

        obj = Basic.__new__(cls, name_symbol, typ, **kw_args)

        obj._name = obj.args[0].name
        obj._rank = len(obj.index_types)
        obj._symmetry = typ.symmetry
        obj._comm = comm2i
        return obj

    @property
    def name(self):
        return self._name

    @property
    def rank(self):
        return self._rank

    @property
    def symmetry(self):
        return self._symmetry

    @property
    def typ(self):
        return self.args[1]

    @property
    def comm(self):
        return self._comm

    @property
    def types(self):
        return self.args[1].types[:]

    @property
    def index_types(self):
        return self.args[1].index_types[:]

    def __lt__(self, other):
        return (self.name, self.index_types) < (other.name, other.index_types)

    def commutes_with(self, other):
        """
        Returns ``0`` if ``self`` and ``other`` commute, ``1`` if they anticommute.

        Returns ``None`` if ``self`` and ``other`` neither commute nor anticommute.
        """
        r = TensorManager.get_comm(self._comm, other._comm)
        return r

    def _print(self):
        return '%s(%s)' %(self.name, ','.join([str(x) for x in self.index_types]))

    def __call__(self, *indices, **kw_args):
        """
        Returns a tensor with indices.

        There is a special behavior in case of indices denoted by ``True``,
        they are considered auto-matrix indices, their slots are automatically
        filled, and confer to the tensor the behavior of a matrix or vector
        upon multiplication with another tensor containing auto-matrix indices
        of the same ``TensorIndexType``. This means indices get summed over the
        same way as in matrix multiplication. For matrix behavior, define two
        auto-matrix indices, for vector behavior define just one.

        Examples
        ========

        >>> from sympy.tensor.tensor import TensorIndexType, tensor_indices, tensorhead
        >>> Lorentz = TensorIndexType('Lorentz', dummy_fmt='L')
        >>> a, b = tensor_indices('a,b', Lorentz)
        >>> A = tensorhead('A', [Lorentz]*2, [[1]*2])
        >>> t = A(a, -b)
        >>> t
        A(a, -b)

        """
        tensor = Tensor._new_with_dummy_replacement(self, indices, **kw_args)
        return tensor

    def __pow__(self, other):
        if self.data is None:
            raise ValueError("No power on abstract tensors.")
        from .array import tensorproduct, tensorcontraction
        metrics = [_.data for _ in self.args[1].args[0]]

        marray = self.data
        marraydim = marray.rank()
        for metric in metrics:
            marray = tensorproduct(marray, metric, marray)
            marray = tensorcontraction(marray, (0, marraydim), (marraydim+1, marraydim+2))

        return marray ** (Rational(1, 2) * other)

    @property
    def data(self):
        return _tensor_data_substitution_dict[self]

    @data.setter
    def data(self, data):
        _tensor_data_substitution_dict[self] = data

    @data.deleter
    def data(self):
        if self in _tensor_data_substitution_dict:
            del _tensor_data_substitution_dict[self]

    def __iter__(self):
        return self.data.__iter__()

    def _components_data_full_destroy(self):
        """
        EXPERIMENTAL: do not rely on this API method.

        Destroy components data associated to the ``TensorHead`` object, this
        checks for attached components data, and destroys components data too.
        """
        # do not garbage collect Kronecker tensor (it should be done by
        # ``TensorIndexType`` garbage collection)
        if self.name == "KD":
            return

        # the data attached to a tensor must be deleted only by the TensorHead
        # destructor. If the TensorHead is deleted, it means that there are no
        # more instances of that tensor anywhere.
        if self in _tensor_data_substitution_dict:
            del _tensor_data_substitution_dict[self]


def _get_argtree_pos(expr, pos):
    for p in pos:
        expr = expr.args[p]
    return expr


class TensExpr(Basic):
    """
    Abstract base class for tensor expressions

    Notes
    =====

    A tensor expression is an expression formed by tensors;
    currently the sums of tensors are distributed.

    A ``TensExpr`` can be a ``TensAdd`` or a ``TensMul``.

    ``TensAdd`` objects are put in canonical form using the Butler-Portugal
    algorithm for canonicalization under monoterm symmetries.

    ``TensMul`` objects are formed by products of component tensors,
    and include a coefficient, which is a SymPy expression.


    In the internal representation contracted indices are represented
    by ``(ipos1, ipos2, icomp1, icomp2)``, where ``icomp1`` is the position
    of the component tensor with contravariant index, ``ipos1`` is the
    slot which the index occupies in that component tensor.

    Contracted indices are therefore nameless in the internal representation.
    """

    _op_priority = 12.0
    is_commutative = False

    def __neg__(self):
        return self*S.NegativeOne

    def __abs__(self):
        raise NotImplementedError

    def __add__(self, other):
        raise NotImplementedError

    def __radd__(self, other):
        raise NotImplementedError

    def __sub__(self, other):
        raise NotImplementedError

    def __rsub__(self, other):
        raise NotImplementedError

    def __mul__(self, other):
        raise NotImplementedError

    def __rmul__(self, other):
        raise NotImplementedError

    def __pow__(self, other):
        if self.data is None:
            raise ValueError("No power without ndarray data.")
        from .array import tensorproduct, tensorcontraction
        free = self.free
        marray = self.data
        mdim = marray.rank()
        for metric in free:
            marray = tensorcontraction(
                tensorproduct(
                marray,
                metric[0].tensor_index_type.data,
                marray),
                (0, mdim), (mdim+1, mdim+2)
            )
        return marray ** (Rational(1, 2) * other)

    def __rpow__(self, other):
        raise NotImplementedError

    def __div__(self, other):
        raise NotImplementedError

    def __rdiv__(self, other):
        raise NotImplementedError()

    __truediv__ = __div__
    __rtruediv__ = __rdiv__

    def fun_eval(self, *index_tuples):
        """
        Return a tensor with free indices substituted according to ``index_tuples``

        ``index_types`` list of tuples ``(old_index, new_index)``

        Examples
        ========

        >>> from sympy.tensor.tensor import TensorIndexType, tensor_indices, tensorhead
        >>> Lorentz = TensorIndexType('Lorentz', dummy_fmt='L')
        >>> i, j, k, l = tensor_indices('i,j,k,l', Lorentz)
        >>> A, B = tensorhead('A,B', [Lorentz]*2, [[1]*2])
        >>> t = A(i, k)*B(-k, -j); t
        A(i, L_0)*B(-L_0, -j)
        >>> t.fun_eval((i, k),(-j, l))
        A(k, L_0)*B(-L_0, l)
        """
        index_tuples = dict(index_tuples)
        indices = self.get_indices()
        free_ind_set = self._get_free_indices_set()
        for i, ind in enumerate(indices):
            if ind in index_tuples and ind in free_ind_set:
                indices[i] = index_tuples[ind]

        indstruc = _IndexStructure.from_indices(*indices)
        return self._set_new_index_structure(indstruc)

    def get_matrix(self):
        """
        Returns ndarray components data as a matrix, if components data are
        available and ndarray dimension does not exceed 2.

        Examples
        ========

        >>> from sympy.tensor.tensor import TensorIndexType, tensorsymmetry, TensorType
        >>> from sympy import ones
        >>> Lorentz = TensorIndexType('Lorentz', dummy_fmt='L')
        >>> sym2 = tensorsymmetry([1]*2)
        >>> S2 = TensorType([Lorentz]*2, sym2)
        >>> A = S2('A')

        The tensor ``A`` is symmetric in its indices, as can be deduced by the
        ``[1, 1]`` Young tableau when constructing `sym2`. One has to be
        careful to assign symmetric component data to ``A``, as the symmetry
        properties of data are currently not checked to be compatible with the
        defined tensor symmetry.

        >>> from sympy.tensor.tensor import tensor_indices, tensorhead
        >>> Lorentz.data = [1, -1, -1, -1]
        >>> i0, i1 = tensor_indices('i0:2', Lorentz)
        >>> A.data = [[j+i for j in range(4)] for i in range(4)]
        >>> A(i0, i1).get_matrix()
        Matrix([
        [0, 1, 2, 3],
        [1, 2, 3, 4],
        [2, 3, 4, 5],
        [3, 4, 5, 6]])

        It is possible to perform usual operation on matrices, such as the
        matrix multiplication:

        >>> A(i0, i1).get_matrix()*ones(4, 1)
        Matrix([
        [ 6],
        [10],
        [14],
        [18]])
        """
        if 0 < self.rank <= 2:
            rows = self.data.shape[0]
            columns = self.data.shape[1] if self.rank == 2 else 1
            if self.rank == 2:
                mat_list = [] * rows
                for i in range(rows):
                    mat_list.append([])
                    for j in range(columns):
                        mat_list[i].append(self[i, j])
            else:
                mat_list = [None] * rows
                for i in range(rows):
                    mat_list[i] = self[i]
            return Matrix(mat_list)
        else:
            raise NotImplementedError(
                "missing multidimensional reduction to matrix.")

    def _get_free_indices_set(self):
        indset = set([])
        for arg in self.args:
            if isinstance(arg, TensExpr):
                indset.update(arg._get_free_indices_set())
        return indset

    def _get_dummy_indices_set(self):
        indset = set([])
        for arg in self.args:
            if isinstance(arg, TensExpr):
                indset.update(arg._get_dummy_indices_set())
        return indset

    def _get_indices_set(self):
        indset = set([])
        for arg in self.args:
            if isinstance(arg, TensExpr):
                indset.update(arg._get_indices_set())
        return indset

    @property
    def _iterate_dummy_indices(self):
        dummy_set = self._get_dummy_indices_set()

        def recursor(expr, pos):
            if isinstance(expr, TensorIndex):
                if expr in dummy_set:
                    yield (expr, pos)
            elif isinstance(expr, (Tuple, TensExpr)):
                for p, arg in enumerate(expr.args):
                    for i in recursor(arg, pos+(p,)):
                        yield i

        return recursor(self, ())

    @property
    def _iterate_free_indices(self):
        free_set = self._get_free_indices_set()

        def recursor(expr, pos):
            if isinstance(expr, TensorIndex):
                if expr in free_set:
                    yield (expr, pos)
            elif isinstance(expr, (Tuple, TensExpr)):
                for p, arg in enumerate(expr.args):
                    for i in recursor(arg, pos+(p,)):
                        yield i

        return recursor(self, ())

    @property
    def _iterate_indices(self):
        def recursor(expr, pos):
            if isinstance(expr, TensorIndex):
                yield (expr, pos)
            elif isinstance(expr, (Tuple, TensExpr)):
                for p, arg in enumerate(expr.args):
                    for i in recursor(arg, pos+(p,)):
                        yield i

        return recursor(self, ())


class TensAdd(TensExpr):
    """
    Sum of tensors

    Parameters
    ==========

    free_args : list of the free indices

    Attributes
    ==========

    ``args`` : tuple of addends
    ``rank`` : rank of the tensor
    ``free_args`` : list of the free indices in sorted order

    Notes
    =====

    Sum of more than one tensor are put automatically in canonical form.

    Examples
    ========

    >>> from sympy.tensor.tensor import TensorIndexType, tensorhead, tensor_indices
    >>> Lorentz = TensorIndexType('Lorentz', dummy_fmt='L')
    >>> a, b = tensor_indices('a,b', Lorentz)
    >>> p, q = tensorhead('p,q', [Lorentz], [[1]])
    >>> t = p(a) + q(a); t
    p(a) + q(a)
    >>> t(b)
    p(b) + q(b)

    Examples with components data added to the tensor expression:

    >>> Lorentz.data = [1, -1, -1, -1]
    >>> a, b = tensor_indices('a, b', Lorentz)
    >>> p.data = [2, 3, -2, 7]
    >>> q.data = [2, 3, -2, 7]
    >>> t = p(a) + q(a); t
    p(a) + q(a)
    >>> t(b)
    p(b) + q(b)

    The following are: 2**2 - 3**2 - 2**2 - 7**2 ==> -58

    >>> (p(a)*p(-a)).data
    -58
    >>> p(a)**2
    -58
    """

    def __new__(cls, *args, **kw_args):
        args = [sympify(x) for x in args if x]
        args = TensAdd._tensAdd_flatten(args)

        if not args:
            return S.Zero

        if len(args) == 1 and not isinstance(args[0], TensExpr):
            return args[0]

        # now check that all addends have the same indices:
        TensAdd._tensAdd_check(args)

        # if TensAdd has only 1 element in its `args`:
        if len(args) == 1:  # and isinstance(args[0], TensMul):
            return args[0]

        # TODO: do not or do canonicalize by default?
        # Technically, one may wish to have additions of non-canonicalized
        # tensors. This feature should be removed in the future.
        # Unfortunately this would require to rewrite a lot of tests.
        # canonicalize all TensMul
        args = [canon_bp(x) for x in args if x]

        # After canonicalization, remove zeros:
        args = [x for x in args if x]

        # if there are no more args (i.e. have cancelled out),
        # just return zero:
        if not args:
            return S.Zero

        if len(args) == 1:
            return args[0]

        # Collect terms appearing more than once, differing by their coefficients:
        args = TensAdd._tensAdd_collect_terms(args)

        # collect canonicalized terms
        def sort_key(t):
            x = get_index_structure(t)
            if not isinstance(t, TensExpr):
                return ([], [], [])
            return (t.components, x.free, x.dum)
        args.sort(key=sort_key)

        if not args:
            return S.Zero
        # it there is only a component tensor return it
        if len(args) == 1:
            return args[0]

        obj = Basic.__new__(cls, *args, **kw_args)
        return obj

    @staticmethod
    def _tensAdd_flatten(args):
        # flatten TensAdd, coerce terms which are not tensors to tensors

        if not all(isinstance(x, TensExpr) for x in args):
            args1 = []
            for x in args:
                if isinstance(x, TensExpr):
                    if isinstance(x, TensAdd):
                        args1.extend(list(x.args))
                    else:
                        args1.append(x)
            args1 = [x for x in args1 if x.coeff != 0]
            args2 = [x for x in args if not isinstance(x, TensExpr)]
            t1 = TensMul.from_data(Add(*args2), [], [], [])
            args = [t1] + args1

        a = []
        for x in args:
            if isinstance(x, TensAdd):
                a.extend(list(x.args))
            else:
                a.append(x)

        args = [x for x in a if x.coeff]
        return args

    @staticmethod
    def _tensAdd_check(args):
        # check that all addends have the same free indices
        indices0 = set([x[0] for x in get_index_structure(args[0]).free])
        list_indices = [set([y[0] for y in get_index_structure(x).free]) for x in args[1:]]
        if not all(x == indices0 for x in list_indices):
            raise ValueError('all tensors must have the same indices')

    @staticmethod
    def _tensAdd_collect_terms(args):
        # collect TensMul terms differing at most by their coefficient
        terms_dict = defaultdict(list)
        scalars = S.Zero
        if isinstance(args[0], TensExpr):
            free_indices = set(args[0].get_free_indices())
        else:
            free_indices = set([])

        for arg in args:
            if not isinstance(arg, TensExpr):
                if free_indices != set([]):
                    raise ValueError("wrong valence")
                scalars += arg
                continue
            if free_indices != set(arg.get_free_indices()):
                raise ValueError("wrong valence")
            # TODO: what is the part which is not a coeff?
            # needs an implementation similar to .as_coeff_Mul()
            terms_dict[arg.nocoeff].append(arg.coeff)

        new_args = [TensMul(Add(*coeff), t) for t, coeff in terms_dict.items() if Add(*coeff) != 0]
        if isinstance(scalars, Add):
            new_args = list(scalars.args) + new_args
        elif scalars != 0:
            new_args = [scalars] + new_args
        return new_args

    @property
    def rank(self):
        return self.args[0].rank

    @property
    def free_args(self):
        return self.args[0].free_args

    def __call__(self, *indices):
        """Returns tensor with ordered free indices replaced by ``indices``

        Parameters
        ==========

        indices

        Examples
        ========

        >>> from sympy import Symbol
        >>> from sympy.tensor.tensor import TensorIndexType, tensor_indices, tensorhead
        >>> D = Symbol('D')
        >>> Lorentz = TensorIndexType('Lorentz', dim=D, dummy_fmt='L')
        >>> i0,i1,i2,i3,i4 = tensor_indices('i0:5', Lorentz)
        >>> p, q = tensorhead('p,q', [Lorentz], [[1]])
        >>> g = Lorentz.metric
        >>> t = p(i0)*p(i1) + g(i0,i1)*q(i2)*q(-i2)
        >>> t(i0,i2)
        metric(i0, i2)*q(L_0)*q(-L_0) + p(i0)*p(i2)
        >>> t(i0,i1) - t(i1,i0)
        0
        """
        free_args = self.free_args
        indices = list(indices)
        if [x.tensor_index_type for x in indices] != [x.tensor_index_type for x in free_args]:
            raise ValueError('incompatible types')
        if indices == free_args:
            return self
        index_tuples = list(zip(free_args, indices))
        a = [x.func(*x.fun_eval(*index_tuples).args) for x in self.args]
        res = TensAdd(*a)
        return res

    def canon_bp(self):
        """
        canonicalize using the Butler-Portugal algorithm for canonicalization
        under monoterm symmetries.
        """
        args = [canon_bp(x) for x in self.args]
        res = TensAdd(*args)
        return res

    def equals(self, other):
        other = sympify(other)
        if isinstance(other, TensMul) and other._coeff == 0:
            return all(x._coeff == 0 for x in self.args)
        if isinstance(other, TensExpr):
            if self.rank != other.rank:
                return False
        if isinstance(other, TensAdd):
            if set(self.args) != set(other.args):
                return False
            else:
                return True
        t = self - other
        if not isinstance(t, TensExpr):
            return t == 0
        else:
            if isinstance(t, TensMul):
                return t._coeff == 0
            else:
                return all(x._coeff == 0 for x in t.args)

    def __add__(self, other):
        return TensAdd(self, other)

    def __radd__(self, other):
        return TensAdd(other, self)

    def __sub__(self, other):
        return TensAdd(self, -other)

    def __rsub__(self, other):
        return TensAdd(other, -self)

    def __mul__(self, other):
        return TensAdd(*(x*other for x in self.args))

    def __rmul__(self, other):
        return self*other

    def __div__(self, other):
        other = sympify(other)
        if isinstance(other, TensExpr):
            raise ValueError('cannot divide by a tensor')
        return TensAdd(*(x/other for x in self.args))

    def __rdiv__(self, other):
        raise ValueError('cannot divide by a tensor')

    def __getitem__(self, item):
        return self.data[item]

    __truediv__ = __div__
    __truerdiv__ = __rdiv__

    def contract_delta(self, delta):
        args = [x.contract_delta(delta) for x in self.args]
        t = TensAdd(*args)
        return canon_bp(t)

    def contract_metric(self, g):
        """
        Raise or lower indices with the metric ``g``

        Parameters
        ==========

        g :  metric

        contract_all : if True, eliminate all ``g`` which are contracted

        Notes
        =====

        see the ``TensorIndexType`` docstring for the contraction conventions
        """

        args = [contract_metric(x, g) for x in self.args]
        t = TensAdd(*args)
        return canon_bp(t)

    def fun_eval(self, *index_tuples):
        """
        Return a tensor with free indices substituted according to ``index_tuples``

        Parameters
        ==========

        index_types : list of tuples ``(old_index, new_index)``

        Examples
        ========

        >>> from sympy.tensor.tensor import TensorIndexType, tensor_indices, tensorhead
        >>> Lorentz = TensorIndexType('Lorentz', dummy_fmt='L')
        >>> i, j, k, l = tensor_indices('i,j,k,l', Lorentz)
        >>> A, B = tensorhead('A,B', [Lorentz]*2, [[1]*2])
        >>> t = A(i, k)*B(-k, -j) + A(i, -j)
        >>> t.fun_eval((i, k),(-j, l))
        A(k, L_0)*B(l, -L_0) + A(k, l)
        """
        args = self.args
        args1 = []
        for x in args:
            y = x.fun_eval(*index_tuples)
            args1.append(y)
        return TensAdd(*args1)

    def substitute_indices(self, *index_tuples):
        """
        Return a tensor with free indices substituted according to ``index_tuples``

        Parameters
        ==========

        index_types : list of tuples ``(old_index, new_index)``

        Examples
        ========

        >>> from sympy.tensor.tensor import TensorIndexType, tensor_indices, tensorhead
        >>> Lorentz = TensorIndexType('Lorentz', dummy_fmt='L')
        >>> i, j, k, l = tensor_indices('i,j,k,l', Lorentz)
        >>> A, B = tensorhead('A,B', [Lorentz]*2, [[1]*2])
        >>> t = A(i, k)*B(-k, -j); t
        A(i, L_0)*B(-L_0, -j)
        >>> t.substitute_indices((i,j), (j, k))
        A(j, L_0)*B(-L_0, -k)
        """
        args = self.args
        args1 = []
        for x in args:
            y = x.substitute_indices(*index_tuples)
            args1.append(y)
        return TensAdd(*args1)

    def _print(self):
        a = []
        args = self.args
        for x in args:
            a.append(str(x))
        a.sort()
        s = ' + '.join(a)
        s = s.replace('+ -', '- ')
        return s

    @property
    def data(self):
        return _tensor_data_substitution_dict[self]

    @data.setter
    def data(self, data):
        _tensor_data_substitution_dict[self] = data

    @data.deleter
    def data(self):
        if self in _tensor_data_substitution_dict:
            del _tensor_data_substitution_dict[self]

    def __iter__(self):
        if not self.data:
            raise ValueError("No iteration on abstract tensors")
        return self.data.flatten().__iter__()


class Tensor(TensExpr):
    """
    Base tensor class, i.e. this represents a tensor, the single unit to be
    put into an expression.

    This object is usually created from a ``TensorHead``, by attaching indices
    to it. Indices preceded by a minus sign are considered contravariant,
    otherwise covariant.

    Examples
    ========

    >>> from sympy.tensor.tensor import TensorIndexType, tensor_indices, tensorhead
    >>> Lorentz = TensorIndexType("Lorentz", dummy_fmt="L")
    >>> mu, nu = tensor_indices('mu nu', Lorentz)
    >>> A = tensorhead("A", [Lorentz, Lorentz], [[1], [1]])
    >>> A(mu, -nu)
    A(mu, -nu)
    >>> A(mu, -mu)
    A(L_0, -L_0)

    """

    is_commutative = False

    def __new__(cls, tensor_head, indices, **kw_args):
        is_canon_bp = kw_args.pop('is_canon_bp', False)
        obj = Basic.__new__(cls, tensor_head, Tuple(*indices), **kw_args)
        obj._index_structure = _IndexStructure.from_indices(*indices)
        if tensor_head.rank != len(indices):
            raise ValueError("wrong number of indices")
        obj._indices = indices
        obj._is_canon_bp = is_canon_bp
        obj._index_map = Tensor._build_index_map(indices, obj._index_structure)
        return obj

    @staticmethod
    def _build_index_map(indices, index_structure):
        index_map = {}
        for idx in indices:
            index_map[idx] = (indices.index(idx),)
        return index_map

    @staticmethod
    def _new_with_dummy_replacement(tensor_head, indices, **kw_args):
        index_structure = _IndexStructure.from_indices(*indices)
        indices = index_structure.get_indices()
        return Tensor(tensor_head, indices, **kw_args)

    def _set_new_index_structure(self, im, is_canon_bp=False):
        indices = im.get_indices()
        return self._set_indices(*indices, is_canon_bp=is_canon_bp)

    def _set_indices(self, *indices, **kw_args):
        if len(indices) != self.ext_rank:
            raise ValueError("indices length mismatch")
        return self.func(self.args[0], indices, is_canon_bp=kw_args.pop('is_canon_bp', False))

    def _get_free_indices_set(self):
        return set([i[0] for i in self._index_structure.free])

    def _get_dummy_indices_set(self):
        dummy_pos = set(itertools.chain(*self._index_structure.dum))
        return set(idx for i, idx in enumerate(self.args[1]) if i in dummy_pos)

    def _get_indices_set(self):
        return set(self.args[1].args)

    @property
    def is_canon_bp(self):
        return self._is_canon_bp

    @property
    def indices(self):
        return self._indices

    @property
    def free(self):
        return self._index_structure.free[:]

    @property
    def free_in_args(self):
        return [(ind, pos, 0) for ind, pos in self.free]

    @property
    def dum(self):
        return self._index_structure.dum[:]

    @property
    def dum_in_args(self):
        return [(p1, p2, 0, 0) for p1, p2 in self.dum]

    @property
    def rank(self):
        return len(self.free)

    @property
    def ext_rank(self):
        return self._index_structure._ext_rank

    @property
    def free_args(self):
        return sorted([x[0] for x in self.free])

    def commutes_with(self, other):
        """
        :param other:
        :return:
            0  commute
            1  anticommute
            None  neither commute nor anticommute
        """
        if not isinstance(other, TensExpr):
            return 0
        elif isinstance(other, Tensor):
            return self.component.commutes_with(other.component)
        return NotImplementedError

    def perm2tensor(self, g, is_canon_bp=False):
        """
        Returns the tensor corresponding to the permutation ``g``

        For further details, see the method in ``TIDS`` with the same name.
        """
        return perm2tensor(self, g, is_canon_bp)

    def canon_bp(self):
        if self._is_canon_bp:
            return self
        g, dummies, msym = self._index_structure.indices_canon_args()
        v = components_canon_args([self.component])
        can = canonicalize(g, dummies, msym, *v)
        if can == 0:
            return S.Zero
        tensor = self.perm2tensor(can, True)
        return tensor

    @property
    def index_types(self):
        return list(self.component.index_types)

    @property
    def coeff(self):
        return S.One

    @property
    def nocoeff(self):
        return self

    @property
    def component(self):
        return self.args[0]

    @property
    def components(self):
        return [self.args[0]]

    def split(self):
        return [self]

    def expand(self):
        return self

    def sorted_components(self):
        return self

    def get_indices(self):
        """
        Get a list of indices, corresponding to those of the tensor.
        """
        return self._index_structure.get_indices()

    def get_free_indices(self):
        """
        Get a list of free indices, corresponding to those of the tensor.
        """
        return self._index_structure.get_free_indices()

    def as_base_exp(self):
        return self, S.One

    def substitute_indices(self, *index_tuples):
        return substitute_indices(self, *index_tuples)

    def __call__(self, *indices):
        """Returns tensor with ordered free indices replaced by ``indices``

        Examples
        ========

        >>> from sympy.tensor.tensor import TensorIndexType, tensor_indices, tensorhead
        >>> Lorentz = TensorIndexType('Lorentz', dummy_fmt='L')
        >>> i0,i1,i2,i3,i4 = tensor_indices('i0:5', Lorentz)
        >>> A = tensorhead('A', [Lorentz]*5, [[1]*5])
        >>> t = A(i2, i1, -i2, -i3, i4)
        >>> t
        A(L_0, i1, -L_0, -i3, i4)
        >>> t(i1, i2, i3)
        A(L_0, i1, -L_0, i2, i3)
        """

        free_args = self.free_args
        indices = list(indices)
        if [x.tensor_index_type for x in indices] != [x.tensor_index_type for x in free_args]:
            raise ValueError('incompatible types')
        if indices == free_args:
            return self
        t = self.fun_eval(*list(zip(free_args, indices)))

        # object is rebuilt in order to make sure that all contracted indices
        # get recognized as dummies, but only if there are contracted indices.
        if len(set(i if i.is_up else -i for i in indices)) != len(indices):
            return t.func(*t.args)
        return t

    # TODO: put this into TensExpr?
    def __iter__(self):
        return self.data.__iter__()

    # TODO: put this into TensExpr?
    def __getitem__(self, item):
        return self.data[item]

    @property
    def data(self):
        return _tensor_data_substitution_dict[self]

    @data.setter
    def data(self, data):
        # TODO: check data compatibility with properties of tensor.
        _tensor_data_substitution_dict[self] = data

    @data.deleter
    def data(self):
        if self in _tensor_data_substitution_dict:
            del _tensor_data_substitution_dict[self]
        if self.metric in _tensor_data_substitution_dict:
            del _tensor_data_substitution_dict[self.metric]

    def __mul__(self, other):
        if isinstance(other, TensAdd):
            return TensAdd(*[self*arg for arg in other.args])
        tmul = TensMul(self, other)
        return tmul

    def __rmul__(self, other):
        return TensMul(other, self)

    def __div__(self, other):
        if isinstance(other, TensExpr):
            raise ValueError('cannot divide by a tensor')
        return TensMul(self, S.One/other, is_canon_bp=self.is_canon_bp)

    def __rdiv__(self, other):
        raise ValueError('cannot divide by a tensor')

    def __add__(self, other):
        return TensAdd(self, other)

    def __radd__(self, other):
        return TensAdd(other, self)

    def __sub__(self, other):
        return TensAdd(self, -other)

    def __rsub__(self, other):
        return TensAdd(other, self)

    __truediv__ = __div__
    __rtruediv__ = __rdiv__

    def __neg__(self):
        return TensMul(S.NegativeOne, self, is_canon_bp=self._is_canon_bp)

    def _print(self):
        indices = [str(ind) for ind in self.indices]
        component = self.component
        if component.rank > 0:
            return ('%s(%s)' % (component.name, ', '.join(indices)))
        else:
            return ('%s' % component.name)

    def equals(self, other):
        if other == 0:
            return self.coeff == 0
        other = sympify(other)
        if not isinstance(other, TensExpr):
            assert not self.components
            return S.One == other

        def _get_compar_comp(self):
            t = self.canon_bp()
            r = (t.coeff, tuple(t.components), \
                    tuple(sorted(t.free)), tuple(sorted(t.dum)))
            return r

        return _get_compar_comp(self) == _get_compar_comp(other)

    def contract_metric(self, g):
        # if metric is not the same, ignore this step:
        if self.component != g:
            return self
        # in case there are free components, do not perform anything:
        if len(self.free) != 0:
            return self

        antisym = g.index_types[0].metric_antisym
        sign = S.One
        typ = g.index_types[0]

        if not antisym:
            # g(i, -i)
            if typ._dim is None:
                raise ValueError('dimension not assigned')
            sign = sign*typ._dim
        else:
            # g(i, -i)
            if typ._dim is None:
                raise ValueError('dimension not assigned')
            sign = sign*typ._dim

            dp0, dp1 = self.dum[0]
            if dp0 < dp1:
                # g(i, -i) = -D with antisymmetric metric
                sign = -sign

        return sign

    def contract_delta(self, metric):
        return self.contract_metric(metric)


class TensMul(TensExpr):
    """
    Product of tensors

    Parameters
    ==========

    coeff : SymPy coefficient of the tensor
    args

    Attributes
    ==========

    ``components`` : list of ``TensorHead`` of the component tensors
    ``types`` : list of nonrepeated ``TensorIndexType``
    ``free`` : list of ``(ind, ipos, icomp)``, see Notes
    ``dum`` : list of ``(ipos1, ipos2, icomp1, icomp2)``, see Notes
    ``ext_rank`` : rank of the tensor counting the dummy indices
    ``rank`` : rank of the tensor
    ``coeff`` : SymPy coefficient of the tensor
    ``free_args`` : list of the free indices in sorted order
    ``is_canon_bp`` : ``True`` if the tensor in in canonical form

    Notes
    =====

    ``args[0]``   list of ``TensorHead`` of the component tensors.

    ``args[1]``   list of ``(ind, ipos, icomp)``
    where ``ind`` is a free index, ``ipos`` is the slot position
    of ``ind`` in the ``icomp``-th component tensor.

    ``args[2]`` list of tuples representing dummy indices.
    ``(ipos1, ipos2, icomp1, icomp2)`` indicates that the contravariant
    dummy index is the ``ipos1``-th slot position in the ``icomp1``-th
    component tensor; the corresponding covariant index is
    in the ``ipos2`` slot position in the ``icomp2``-th component tensor.

    """

    def __new__(cls, *args, **kw_args):
        # make sure everything is sympified:
        args = [sympify(arg) for arg in args]

        # flatten:
        args = TensMul._flatten(args)

        is_canon_bp = kw_args.get('is_canon_bp', False)
        args, indices, free, dum = TensMul._tensMul_contract_indices(args)

        index_types = []
        for t in args:
            if not isinstance(t, TensExpr):
                continue
            index_types.extend(t.index_types)
        index_structure = _IndexStructure(free, dum, index_types, indices, canon_bp=is_canon_bp)

        if any([isinstance(arg, TensAdd) for arg in args]):
            add_args = TensAdd._tensAdd_flatten(args)
            return TensAdd(*add_args)
        coeff = reduce(lambda a, b: a*b, [S.One] + [arg for arg in args if not isinstance(arg, TensExpr)])
        args = [arg for arg in args if isinstance(arg, TensExpr)]
        TensMul._rebuild_tensors_list(args, index_structure)

        if coeff != 1:
            args = [coeff] + args
        if len(args) == 1:
            return args[0]

        obj = Basic.__new__(cls, *args)
        obj._index_types = index_types
        obj._index_structure = index_structure
        obj._ext_rank = len(obj._index_structure.free) + 2*len(obj._index_structure.dum)
        obj._coeff = coeff
        obj._is_canon_bp = is_canon_bp
        return obj

    @staticmethod
    def _tensMul_contract_indices(args):
        f_ext_rank = 0
        free = []
        dum = []

        index_up = lambda u: u if u.is_up else -u

        indices = list(itertools.chain(*[get_indices(arg) for arg in args]))

        def standardize_matrix_free_indices(arg):
            type_counter = defaultdict(int)
            indices = arg.get_indices()
            arg = arg._set_indices(*indices)
            return arg

        for arg in args:
            if not isinstance(arg, TensExpr):
                continue

            arg = standardize_matrix_free_indices(arg)

            free_dict1 = dict([(index_up(i), (pos, i)) for i, pos in free])
            free_dict2 = dict([(index_up(i), (pos, i)) for i, pos in arg.free])

            mat_dict1 = dict([(i, pos) for i, pos in free])
            mat_dict2 = dict([(i, pos) for i, pos in arg.free])

            # Get a set containing all indices to contract in upper form:
            indices_to_contract = set(free_dict1.keys()) & set(free_dict2.keys())

            for name in indices_to_contract:
                ipos1, ind1 = free_dict1[name]
                ipos2, ind2 = free_dict2[name]
                ipos2pf = ipos2 + f_ext_rank
                if ind1.is_up == ind2.is_up:
                    raise ValueError('wrong index construction {0}'.format(ind1))
                # Create a new dummy indices pair:
                if ind1.is_up:
                    new_dummy = (ipos1, ipos2pf)
                else:
                    new_dummy = (ipos2pf, ipos1)
                dum.append(new_dummy)

            # Matrix indices check:
            mat_keys1 = set(mat_dict1.keys())
            mat_keys2 = set(mat_dict2.keys())

            mat_types_map1 = defaultdict(set)
            mat_types_map2 = defaultdict(set)

            for (i, pos) in mat_dict1.items():
                mat_types_map1[i.tensor_index_type].add(i)
            for (i, pos) in mat_dict2.items():
                mat_types_map2[i.tensor_index_type].add(i)

            mat_contraction = mat_keys1 & mat_keys2
            mat_skip = set([])
            mat_free = []

            # Contraction of matrix indices is a bit more complicated,
            # because it is governed by more complicated rules:
            for mi in mat_contraction:
                if not mi.is_up:
                    continue

                mat_types_map1[mi.tensor_index_type].discard(mi)
                mat_types_map2[mi.tensor_index_type].discard(mi)

                negmi1 = mat_types_map1[mi.tensor_index_type].pop() if mat_types_map1[mi.tensor_index_type] else None
                negmi2 = mat_types_map2[mi.tensor_index_type].pop() if mat_types_map2[mi.tensor_index_type] else None

                mat_skip.update([mi, negmi1, negmi2])

                ipos1 = mat_dict1[mi]
                ipos2 = mat_dict2[mi]
                ipos2pf = ipos2 + f_ext_rank

                # Case A(m0)*B(m0) ==> A(-D)*B(D):
                if (negmi1 not in mat_keys1) and (negmi2 not in mat_keys2):
                    dum.append((ipos2pf, ipos1))
                # Case A(m0, -m1)*B(m0) ==> A(m0, -D)*B(D):
                elif (negmi1 in mat_keys1) and (negmi2 not in mat_keys2):
                    mpos1 = mat_dict1[negmi1]
                    dum.append((ipos2pf, mpos1))
                    mat_free.append((mi, ipos1))
                    indices[ipos1] = mi
                # Case A(m0)*B(m0, -m1) ==> A(-D)*B(D, m0):
                elif (negmi1 not in mat_keys1) and (negmi2 in mat_keys2):
                    mpos2 = mat_dict2[negmi2]
                    dum.append((ipos2pf, ipos1))
                    mat_free.append((mi, f_ext_rank + mpos2))
                    indices[f_ext_rank + mpos2] = mi
                # Case A(m0, -m1)*B(m0, -m1) ==> A(m0, -D)*B(D, -m1):
                elif (negmi1 in mat_keys1) and (negmi2 in mat_keys2):
                    mpos1 = mat_dict1[negmi1]
                    mpos2 = mat_dict2[negmi2]
                    dum.append((ipos2pf, mpos1))
                    mat_free.append((mi, ipos1))
                    mat_free.append((negmi2, f_ext_rank + mpos2))

            # Update values to the cumulative data structures:
            free = [(ind, i) for ind, i in free if index_up(ind) not in indices_to_contract
                        and ind not in mat_skip]
            free.extend([(ind, i + f_ext_rank) for ind, i in arg.free if index_up(ind) not in indices_to_contract
                        and ind not in mat_skip])
            free.extend(mat_free)
            dum.extend([(i1 + f_ext_rank, i2 + f_ext_rank) for i1, i2 in arg.dum])
            f_ext_rank += arg.ext_rank

        # rename contracted indices:
        indices = _IndexStructure._replace_dummy_names(indices, free, dum)

        # Let's replace these names in the args:
        pos = 0
        newargs = []
        for arg in args:
            if isinstance(arg, TensExpr):
                newargs.append(arg._set_indices(*indices[pos:pos+arg.ext_rank]))
                pos += arg.ext_rank
            else:
                newargs.append(arg)

        return newargs, indices, free, dum

    @staticmethod
    def _get_components_from_args(args):
        """
        Get a list of ``Tensor`` objects having the same ``TIDS`` if multiplied
        by one another.
        """
        components = []
        for arg in args:
            if not isinstance(arg, TensExpr):
                continue
            components.extend(arg.components)
        return components

    @staticmethod
    def _rebuild_tensors_list(args, index_structure):
        indices = index_structure.get_indices()
        #tensors = [None for i in components]  # pre-allocate list
        ind_pos = 0
        for i, arg in enumerate(args):
            if not isinstance(arg, TensExpr):
                continue
            prev_pos = ind_pos
            ind_pos += arg.ext_rank
            args[i] = Tensor(arg.component, indices[prev_pos:ind_pos])

    @staticmethod
    def _flatten(args):
        a = []
        for arg in args:
            if isinstance(arg, TensMul):
                a.extend(arg.args)
            else:
                a.append(arg)
        return a

    # TODO: this method should be private
    # TODO: should this method be renamed _from_components_free_dum ?
    @staticmethod
    def from_data(coeff, components, free, dum, **kw_args):
        return TensMul(coeff, *TensMul._get_tensors_from_components_free_dum(components, free, dum), **kw_args)

    @staticmethod
    def _get_tensors_from_components_free_dum(components, free, dum):
        """
        Get a list of ``Tensor`` objects by distributing ``free`` and ``dum`` indices on the ``components``.
        """
        index_structure = _IndexStructure.from_components_free_dum(components, free, dum)
        indices = index_structure.get_indices()
        tensors = [None for i in components]  # pre-allocate list

        # distribute indices on components to build a list of tensors:
        ind_pos = 0
        for i, component in enumerate(components):
            prev_pos = ind_pos
            ind_pos += component.rank
            tensors[i] = Tensor(component, indices[prev_pos:ind_pos])
        return tensors

    def _get_free_indices_set(self):
        return set([i[0] for i in self.free])

    def _get_dummy_indices_set(self):
        dummy_pos = set(itertools.chain(*self.dum))
        return set(idx for i, idx in enumerate(self._index_structure.get_indices()) if i in dummy_pos)

    def _get_position_offset_for_indices(self):
        arg_offset = [None for i in range(self.ext_rank)]
        counter = 0
        for i, arg in enumerate(self.args):
            if not isinstance(arg, TensExpr):
                continue
            for j in range(arg.ext_rank):
                arg_offset[j + counter] = counter
            counter += arg.ext_rank
        return arg_offset

    @property
    def free_args(self):
        return sorted([x[0] for x in self.free])

    @property
    def components(self):
        return self._get_components_from_args(self.args)

    @property
    def free(self):
        return self._index_structure.free[:]

    @property
    def free_in_args(self):
        arg_offset = self._get_position_offset_for_indices()
        argpos = self._get_indices_to_args_pos()
        return [(ind, pos-arg_offset[pos], argpos[pos]) for (ind, pos) in self.free]

    @property
    def coeff(self):
        return self._coeff

    @property
    def nocoeff(self):
        return self.func(*[t for t in self.args if isinstance(t, TensExpr)])

    @property
    def dum(self):
        return self._index_structure.dum[:]

    @property
    def dum_in_args(self):
        arg_offset = self._get_position_offset_for_indices()
        argpos = self._get_indices_to_args_pos()
        return [(p1-arg_offset[p1], p2-arg_offset[p2], argpos[p1], argpos[p2]) for p1, p2 in self.dum]

    @property
    def rank(self):
        return len(self.free)

    @property
    def ext_rank(self):
        return self._ext_rank

    @property
    def index_types(self):
        return self._index_types[:]

    def equals(self, other):
        if other == 0:
            return self.coeff == 0
        other = sympify(other)
        if not isinstance(other, TensExpr):
            assert not self.components
            return self._coeff == other

        return self.canon_bp() == other.canon_bp()

    def get_indices(self):
        """
        Returns the list of indices of the tensor

        The indices are listed in the order in which they appear in the
        component tensors.
        The dummy indices are given a name which does not collide with
        the names of the free indices.

        Examples
        ========

        >>> from sympy.tensor.tensor import TensorIndexType, tensor_indices, tensorhead
        >>> Lorentz = TensorIndexType('Lorentz', dummy_fmt='L')
        >>> m0, m1, m2 = tensor_indices('m0,m1,m2', Lorentz)
        >>> g = Lorentz.metric
        >>> p, q = tensorhead('p,q', [Lorentz], [[1]])
        >>> t = p(m1)*g(m0,m2)
        >>> t.get_indices()
        [m1, m0, m2]
        >>> t2 = p(m1)*g(-m1, m2)
        >>> t2.get_indices()
        [L_0, -L_0, m2]
        """
        return self._index_structure.get_indices()

    def get_free_indices(self):
        """
        Returns the list of free indices of the tensor

        The indices are listed in the order in which they appear in the
        component tensors.

        Examples
        ========

        >>> from sympy.tensor.tensor import TensorIndexType, tensor_indices, tensorhead
        >>> Lorentz = TensorIndexType('Lorentz', dummy_fmt='L')
        >>> m0, m1, m2 = tensor_indices('m0,m1,m2', Lorentz)
        >>> g = Lorentz.metric
        >>> p, q = tensorhead('p,q', [Lorentz], [[1]])
        >>> t = p(m1)*g(m0,m2)
        >>> t.get_free_indices()
        [m1, m0, m2]
        >>> t2 = p(m1)*g(-m1, m2)
        >>> t2.get_free_indices()
        [m2]
        """
        return self._index_structure.get_free_indices()

    def split(self):
        """
        Returns a list of tensors, whose product is ``self``

        Dummy indices contracted among different tensor components
        become free indices with the same name as the one used to
        represent the dummy indices.

        Examples
        ========

        >>> from sympy.tensor.tensor import TensorIndexType, tensor_indices, tensorhead
        >>> Lorentz = TensorIndexType('Lorentz', dummy_fmt='L')
        >>> a, b, c, d = tensor_indices('a,b,c,d', Lorentz)
        >>> A, B = tensorhead('A,B', [Lorentz]*2, [[1]*2])
        >>> t = A(a,b)*B(-b,c)
        >>> t
        A(a, L_0)*B(-L_0, c)
        >>> t.split()
        [A(a, L_0), B(-L_0, c)]
        """
        if self.args == ():
            return [self]
        splitp = []
        res = 1
        for arg in self.args:
            if isinstance(arg, Tensor):
                splitp.append(res*arg)
                res = 1
            else:
                res *= arg
        return splitp

    def __add__(self, other):
        return TensAdd(self, other)

    def __radd__(self, other):
        return TensAdd(other, self)

    def __sub__(self, other):
        return TensAdd(self, -other)

    def __rsub__(self, other):
        return TensAdd(other, -self)

    def __mul__(self, other):
        """
        Multiply two tensors using Einstein summation convention.

        If the two tensors have an index in common, one contravariant
        and the other covariant, in their product the indices are summed

        Examples
        ========

        >>> from sympy.tensor.tensor import TensorIndexType, tensor_indices, tensorhead
        >>> Lorentz = TensorIndexType('Lorentz', dummy_fmt='L')
        >>> m0, m1, m2 = tensor_indices('m0,m1,m2', Lorentz)
        >>> g = Lorentz.metric
        >>> p, q = tensorhead('p,q', [Lorentz], [[1]])
        >>> t1 = p(m0)
        >>> t2 = q(-m0)
        >>> t1*t2
        p(L_0)*q(-L_0)
        """
        other = sympify(other)
        if not isinstance(other, TensExpr):
            return TensMul(*(self.args + (other,)), is_canon_bp=self._is_canon_bp)
        if isinstance(other, TensAdd):
            return TensAdd(*[self*x for x in other.args])
        if isinstance(other, TensMul):
            return TensMul(*(self.args + other.args))
        return TensMul(*(self.args + (other,)))

    def __rmul__(self, other):
        other = sympify(other)
        return TensMul(*((other,)+self.args), is_canon_bp=self._is_canon_bp)

    def __div__(self, other):
        other = sympify(other)
        if isinstance(other, TensExpr):
            raise ValueError('cannot divide by a tensor')
        return TensMul(*(self.args + (S.One/other,)), is_canon_bp=self._is_canon_bp)

    def __rdiv__(self, other):
        raise ValueError('cannot divide by a tensor')

    def __getitem__(self, item):
        return self.data[item]

    __truediv__ = __div__
    __truerdiv__ = __rdiv__

    def _sort_args_for_sorted_components(self):
        """
        Returns the ``args`` sorted according to the components commutation
        properties.

        The sorting is done taking into account the commutation group
        of the component tensors.
        """
        cv = [arg for arg in self.args if isinstance(arg, TensExpr)]
        sign = 1
        n = len(cv) - 1
        for i in range(n):
            for j in range(n, i, -1):
                c = cv[j-1].commutes_with(cv[j])
                # if `c` is `None`, it does neither commute nor anticommute, skip:
                if c not in [0, 1]:
                    continue
                if (cv[j-1].component.types, cv[j-1].component.name) > \
                        (cv[j].component.types, cv[j].component.name):
                    cv[j-1], cv[j] = cv[j], cv[j-1]
                    # if `c` is 1, the anticommute, so change sign:
                    if c:
                        sign = -sign

        coeff = sign * self.coeff
        if coeff != 1:
            return [coeff] + cv
        return cv

    def sorted_components(self):
        """
        Returns a tensor product with sorted components.
        """
        return TensMul(*self._sort_args_for_sorted_components())

    def perm2tensor(self, g, is_canon_bp=False):
        """
        Returns the tensor corresponding to the permutation ``g``

        For further details, see the method in ``TIDS`` with the same name.
        """
        return perm2tensor(self, g, is_canon_bp=is_canon_bp)

    def canon_bp(self):
        """
        Canonicalize using the Butler-Portugal algorithm for canonicalization
        under monoterm symmetries.

        Examples
        ========

        >>> from sympy.tensor.tensor import TensorIndexType, tensor_indices, tensorhead
        >>> Lorentz = TensorIndexType('Lorentz', dummy_fmt='L')
        >>> m0, m1, m2 = tensor_indices('m0,m1,m2', Lorentz)
        >>> A = tensorhead('A', [Lorentz]*2, [[2]])
        >>> t = A(m0,-m1)*A(m1,-m0)
        >>> t.canon_bp()
        -A(L_0, L_1)*A(-L_0, -L_1)
        >>> t = A(m0,-m1)*A(m1,-m2)*A(m2,-m0)
        >>> t.canon_bp()
        0
        """
        if self._is_canon_bp:
            return self
        if not self.components:
            return self
        t = self.sorted_components()
        g, dummies, msym = t._index_structure.indices_canon_args()
        v = components_canon_args(t.components)
        can = canonicalize(g, dummies, msym, *v)
        if can == 0:
            return S.Zero
        tmul = t.perm2tensor(can, True)
        return tmul

    def contract_delta(self, delta):
        t = self.contract_metric(delta)
        return t

    def _get_indices_to_args_pos(self):
        """
        Get a dict mapping the index position to TensMul's argument number.
        """
        pos_map = dict()
        pos_counter = 0
        for arg_i, arg in enumerate(self.args):
            if not isinstance(arg, TensExpr):
                continue
            assert isinstance(arg, Tensor)
            for i in range(arg.ext_rank):
                pos_map[pos_counter] = arg_i
                pos_counter += 1
        return pos_map

    def contract_metric(self, g):
        """
        Raise or lower indices with the metric ``g``

        Parameters
        ==========

        g : metric

        Notes
        =====

        see the ``TensorIndexType`` docstring for the contraction conventions

        Examples
        ========

        >>> from sympy.tensor.tensor import TensorIndexType, tensor_indices, tensorhead
        >>> Lorentz = TensorIndexType('Lorentz', dummy_fmt='L')
        >>> m0, m1, m2 = tensor_indices('m0,m1,m2', Lorentz)
        >>> g = Lorentz.metric
        >>> p, q = tensorhead('p,q', [Lorentz], [[1]])
        >>> t = p(m0)*q(m1)*g(-m0, -m1)
        >>> t.canon_bp()
        metric(L_0, L_1)*p(-L_0)*q(-L_1)
        >>> t.contract_metric(g).canon_bp()
        p(L_0)*q(-L_0)
        """
        pos_map = self._get_indices_to_args_pos()
        args = list(self.args)

        antisym = g.index_types[0].metric_antisym

        # list of positions of the metric ``g`` inside ``args``
        gpos = [i for i, x in enumerate(self.args) if isinstance(x, Tensor) and x.component == g]
        if not gpos:
            return self

        # Sign is either 1 or -1, to correct the sign after metric contraction
        # (for spinor indices).
        sign = 1
        dum = self.dum[:]
        free = self.free[:]
        elim = set()
        for gposx in gpos:
            if gposx in elim:
                continue
            free1 = [x for x in free if pos_map[x[1]] == gposx]
            dum1 = [x for x in dum if pos_map[x[0]] == gposx or pos_map[x[1]] == gposx]
            if not dum1:
                continue
            elim.add(gposx)
            # subs with the multiplication neutral element, that is, remove it:
            args[gposx] = 1
            if len(dum1) == 2:
                if not antisym:
                    dum10, dum11 = dum1
                    if pos_map[dum10[1]] == gposx:
                        # the index with pos p0 contravariant
                        p0 = dum10[0]
                    else:
                        # the index with pos p0 is covariant
                        p0 = dum10[1]
                    if pos_map[dum11[1]] == gposx:
                        # the index with pos p1 is contravariant
                        p1 = dum11[0]
                    else:
                        # the index with pos p1 is covariant
                        p1 = dum11[1]

                    dum.append((p0, p1))
                else:
                    dum10, dum11 = dum1
                    # change the sign to bring the indices of the metric to contravariant
                    # form; change the sign if dum10 has the metric index in position 0
                    if pos_map[dum10[1]] == gposx:
                        # the index with pos p0 is contravariant
                        p0 = dum10[0]
                        if dum10[1] == 1:
                            sign = -sign
                    else:
                        # the index with pos p0 is covariant
                        p0 = dum10[1]
                        if dum10[0] == 0:
                            sign = -sign
                    if pos_map[dum11[1]] == gposx:
                        # the index with pos p1 is contravariant
                        p1 = dum11[0]
                        sign = -sign
                    else:
                        # the index with pos p1 is covariant
                        p1 = dum11[1]

                    dum.append((p0, p1))

            elif len(dum1) == 1:
                if not antisym:
                    dp0, dp1 = dum1[0]
                    if pos_map[dp0] == pos_map[dp1]:
                        # g(i, -i)
                        typ = g.index_types[0]
                        if typ._dim is None:
                            raise ValueError('dimension not assigned')
                        sign = sign*typ._dim

                    else:
                        # g(i0, i1)*p(-i1)
                        if pos_map[dp0] == gposx:
                            p1 = dp1
                        else:
                            p1 = dp0

                        ind, p = free1[0]
                        free.append((ind, p1))
                else:
                    dp0, dp1 = dum1[0]
                    if pos_map[dp0] == pos_map[dp1]:
                        # g(i, -i)
                        typ = g.index_types[0]
                        if typ._dim is None:
                            raise ValueError('dimension not assigned')
                        sign = sign*typ._dim

                        if dp0 < dp1:
                            # g(i, -i) = -D with antisymmetric metric
                            sign = -sign
                    else:
                        # g(i0, i1)*p(-i1)
                        if pos_map[dp0] == gposx:
                            p1 = dp1
                            if dp0 == 0:
                                sign = -sign
                        else:
                            p1 = dp0
                        ind, p = free1[0]
                        free.append((ind, p1))
            dum = [x for x in dum if x not in dum1]
            free = [x for x in free if x not in free1]

        # shift positions:
        shift = 0
        shifts = [0]*len(args)
        for i in range(len(args)):
            if i in elim:
                shift += 2
                continue
            shifts[i] = shift
        free = [(ind, p - shifts[pos_map[p]]) for (ind, p) in free if pos_map[p] not in elim]
        dum = [(p0 - shifts[pos_map[p0]], p1 - shifts[pos_map[p1]]) for i, (p0, p1) in enumerate(dum) if pos_map[p0] not in elim and pos_map[p1] not in elim]

        res = sign*TensMul(*args)
        if not isinstance(res, TensExpr):
            return res
        im = _IndexStructure.from_components_free_dum(res.components, free, dum)
        return res._set_new_index_structure(im)

    def _set_new_index_structure(self, im, is_canon_bp=False):
        indices = im.get_indices()
        return self._set_indices(*indices, is_canon_bp=is_canon_bp)

    def _set_indices(self, *indices, **kw_args):
        if len(indices) != self.ext_rank:
            raise ValueError("indices length mismatch")
        args = list(self.args)[:]
        pos = 0
        is_canon_bp = kw_args.pop('is_canon_bp', False)
        for i, arg in enumerate(args):
            if not isinstance(arg, TensExpr):
                continue
            assert isinstance(arg, Tensor)
            ext_rank = arg.ext_rank
            args[i] = arg._set_indices(*indices[pos:pos+ext_rank])
            pos += ext_rank
        return TensMul(*args, is_canon_bp=is_canon_bp)

    @staticmethod
    def _index_replacement_for_contract_metric(args, free, dum):
        for arg in args:
            if not isinstance(arg, TensExpr):
                continue
            assert isinstance(arg, Tensor)

    def substitute_indices(self, *index_tuples):
        return substitute_indices(self, *index_tuples)

    def __call__(self, *indices):
        """Returns tensor product with ordered free indices replaced by ``indices``

        Examples
        ========

        >>> from sympy import Symbol
        >>> from sympy.tensor.tensor import TensorIndexType, tensor_indices, tensorhead
        >>> D = Symbol('D')
        >>> Lorentz = TensorIndexType('Lorentz', dim=D, dummy_fmt='L')
        >>> i0,i1,i2,i3,i4 = tensor_indices('i0:5', Lorentz)
        >>> g = Lorentz.metric
        >>> p, q = tensorhead('p,q', [Lorentz], [[1]])
        >>> t = p(i0)*q(i1)*q(-i1)
        >>> t(i1)
        p(i1)*q(L_0)*q(-L_0)
        """
        free_args = self.free_args
        indices = list(indices)
        if [x.tensor_index_type for x in indices] != [x.tensor_index_type for x in free_args]:
            raise ValueError('incompatible types')
        if indices == free_args:
            return self
        t = self.fun_eval(*list(zip(free_args, indices)))

        # object is rebuilt in order to make sure that all contracted indices
        # get recognized as dummies, but only if there are contracted indices.
        if len(set(i if i.is_up else -i for i in indices)) != len(indices):
            return t.func(*t.args)
        return t

    def _print(self):
        args = self.args
        get_str = lambda arg: str(arg) if arg.is_Atom or isinstance(arg, TensExpr) else ("(%s)" % str(arg))

        if not args:
            # no arguments is equivalent to "1", i.e. TensMul().
            # If tensors are constructed correctly, this should never occur.
            return "1"
        if self.coeff == S.NegativeOne:
            # expressions like "-A(a)"
            return "-"+"*".join([get_str(arg) for arg in args[1:]])

        # prints expressions like "A(a)", "3*A(a)", "(1+x)*A(a)"
        return "*".join([get_str(arg) for arg in self.args])

    @property
    def data(self):
        dat = _tensor_data_substitution_dict[self]
        return dat

    @data.setter
    def data(self, data):
        raise ValueError("Not possible to set component data to a tensor expression")

    @data.deleter
    def data(self):
        raise ValueError("Not possible to delete component data to a tensor expression")

    def __iter__(self):
        if self.data is None:
            raise ValueError("No iteration on abstract tensors")
        return self.data.__iter__()


def canon_bp(p):
    """
    Butler-Portugal canonicalization
    """
    if isinstance(p, TensExpr):
        return p.canon_bp()
    return p

def tensor_mul(*a):
    """
    product of tensors
    """
    if not a:
        return TensMul.from_data(S.One, [], [], [])
    t = a[0]
    for tx in a[1:]:
        t = t*tx
    return t


def riemann_cyclic_replace(t_r):
    """
    replace Riemann tensor with an equivalent expression

    ``R(m,n,p,q) -> 2/3*R(m,n,p,q) - 1/3*R(m,q,n,p) + 1/3*R(m,p,n,q)``

    """
    free = sorted(t_r.free, key=lambda x: x[1])
    m, n, p, q = [x[0] for x in free]
    t0 = S(2)/3*t_r
    t1 = - S(1)/3*t_r.substitute_indices((m,m),(n,q),(p,n),(q,p))
    t2 = S(1)/3*t_r.substitute_indices((m,m),(n,p),(p,n),(q,q))
    t3 = t0 + t1 + t2
    return t3

def riemann_cyclic(t2):
    """
    replace each Riemann tensor with an equivalent expression
    satisfying the cyclic identity.

    This trick is discussed in the reference guide to Cadabra.

    Examples
    ========

    >>> from sympy.tensor.tensor import TensorIndexType, tensor_indices, tensorhead, riemann_cyclic
    >>> Lorentz = TensorIndexType('Lorentz', dummy_fmt='L')
    >>> i, j, k, l = tensor_indices('i,j,k,l', Lorentz)
    >>> R = tensorhead('R', [Lorentz]*4, [[2, 2]])
    >>> t = R(i,j,k,l)*(R(-i,-j,-k,-l) - 2*R(-i,-k,-j,-l))
    >>> riemann_cyclic(t)
    0
    """
    if isinstance(t2, (TensMul, Tensor)):
        args = [t2]
    else:
        args = t2.args
    a1 = [x.split() for x in args]
    a2 = [[riemann_cyclic_replace(tx) for tx in y] for y in a1]
    a3 = [tensor_mul(*v) for v in a2]
    t3 = TensAdd(*a3)
    if not t3:
        return t3
    else:
        return canon_bp(t3)


def get_lines(ex, index_type):
    """
    returns ``(lines, traces, rest)`` for an index type,
    where ``lines`` is the list of list of positions of a matrix line,
    ``traces`` is the list of list of traced matrix lines,
    ``rest`` is the rest of the elements ot the tensor.
    """
    def _join_lines(a):
        i = 0
        while i < len(a):
            x = a[i]
            xend = x[-1]
            xstart = x[0]
            hit = True
            while hit:
                hit = False
                for j in range(i + 1, len(a)):
                    if j >= len(a):
                        break
                    if a[j][0] == xend:
                        hit = True
                        x.extend(a[j][1:])
                        xend = x[-1]
                        a.pop(j)
                        continue
                    if a[j][0] == xstart:
                        hit = True
                        a[i] = reversed(a[j][1:]) + x
                        x = a[i]
                        xstart = a[i][0]
                        a.pop(j)
                        continue
                    if a[j][-1] == xend:
                        hit = True
                        x.extend(reversed(a[j][:-1]))
                        xend = x[-1]
                        a.pop(j)
                        continue
                    if a[j][-1] == xstart:
                        hit = True
                        a[i] = a[j][:-1] + x
                        x = a[i]
                        xstart = x[0]
                        a.pop(j)
                        continue
            i += 1
        return a

    arguments = ex.args
    dt = {}
    for c in ex.args:
        if not isinstance(c, TensExpr):
            continue
        if c in dt:
            continue
        index_types = c.index_types
        a = []
        for i in range(len(index_types)):
            if index_types[i] is index_type:
                a.append(i)
        if len(a) > 2:
            raise ValueError('at most two indices of type %s allowed' % index_type)
        if len(a) == 2:
            dt[c] = a
    #dum = ex.dum
    lines = []
    traces = []
    traces1 = []
    #indices_to_args_pos = ex._get_indices_to_args_pos()
    # TODO: add a dum_to_components_map ?
    for p0, p1, c0, c1 in ex.dum_in_args:
        if arguments[c0] not in dt:
            continue
        if c0 == c1:
            traces.append([c0])
            continue
        ta0 = dt[arguments[c0]]
        ta1 = dt[arguments[c1]]
        if p0 not in ta0:
            continue
        if ta0.index(p0) == ta1.index(p1):
            # case gamma(i,s0,-s1) in c0, gamma(j,-s0,s2) in c1;
            # to deal with this case one could add to the position
            # a flag for transposition;
            # one could write [(c0, False), (c1, True)]
            raise NotImplementedError
        # if p0 == ta0[1] then G in pos c0 is mult on the right by G in c1
        # if p0 == ta0[0] then G in pos c1 is mult on the right by G in c0
        ta0 = dt[arguments[c0]]
        b0, b1 = (c0, c1) if p0 == ta0[1]  else (c1, c0)
        lines1 = lines[:]
        for line in lines:
            if line[-1] == b0:
                if line[0] == b1:
                    n = line.index(min(line))
                    traces1.append(line)
                    traces.append(line[n:] + line[:n])
                else:
                    line.append(b1)
                break
            elif line[0] == b1:
                line.insert(0, b0)
                break
        else:
            lines1.append([b0, b1])

        lines = [x for x in lines1 if x not in traces1]
        lines = _join_lines(lines)
    rest = []
    for line in lines:
        for y in line:
            rest.append(y)
    for line in traces:
        for y in line:
            rest.append(y)
    rest = [x for x in range(len(arguments)) if x not in rest]

    return lines, traces, rest


def get_free_indices(t):
    if not isinstance(t, TensExpr):
        return ()
    return t.get_free_indices()


def get_indices(t):
    if not isinstance(t, TensExpr):
        return ()
    return t.get_indices()


def get_index_structure(t):
    if isinstance(t, TensExpr):
        return t._index_structure
    return _IndexStructure([], [], [], [])


def get_coeff(t):
    if isinstance(t, Tensor):
        return S.One
    if isinstance(t, TensMul):
        return t.coeff
    if isinstance(t, TensExpr):
        raise ValueError("no coefficient associated to this tensor expression")
    return t

def contract_metric(t, g):
    if isinstance(t, TensExpr):
        return t.contract_metric(g)
    return t


def perm2tensor(t, g, is_canon_bp=False):
    """
    Returns the tensor corresponding to the permutation ``g``

    For further details, see the method in ``TIDS`` with the same name.
    """
    if not isinstance(t, TensExpr):
        return t
    elif isinstance(t, (Tensor, TensMul)):
        nim = get_index_structure(t).perm2tensor(g, is_canon_bp=is_canon_bp)
        res = t._set_new_index_structure(nim, is_canon_bp=is_canon_bp)
        if g[-1] != len(g) - 1:
            return -res

        return res
    raise NotImplementedError()


def substitute_indices(t, *index_tuples):
    """
    Return a tensor with free indices substituted according to ``index_tuples``

    ``index_types`` list of tuples ``(old_index, new_index)``

    Note: this method will neither raise or lower the indices, it will just replace their symbol.

    Examples
    ========

    >>> from sympy.tensor.tensor import TensorIndexType, tensor_indices, tensorhead
    >>> Lorentz = TensorIndexType('Lorentz', dummy_fmt='L')
    >>> i, j, k, l = tensor_indices('i,j,k,l', Lorentz)
    >>> A, B = tensorhead('A,B', [Lorentz]*2, [[1]*2])
    >>> t = A(i, k)*B(-k, -j); t
    A(i, L_0)*B(-L_0, -j)
    >>> t.substitute_indices((i,j), (j, k))
    A(j, L_0)*B(-L_0, -k)
    """
    if not isinstance(t, TensExpr):
        return t
    free = t.free
    free1 = []
    for j, ipos in free:
        for i, v in index_tuples:
            if i._name == j._name and i.tensor_index_type == j.tensor_index_type:
                if i._is_up == j._is_up:
                    free1.append((v, ipos))
                else:
                    free1.append((-v, ipos))
                break
        else:
            free1.append((j, ipos))

    t = TensMul.from_data(t.coeff, t.components, free1, t.dum)
    return t
