from a_sync.utils.repr import repr_trunc

def test_repr_trunc_list():
  assert repr_trunc(list(range(10)) == "[1, 2, 3, 4, 5, ...]"
                    
def test_repr_trunc_tuple():
  assert repr_trunc(tuple(range(10)) == "(1, 2, 3, 4, 5, ...)"
                    
def test_repr_trunc_dict():
  d = {i: i for i in range(10)}
  assert repr_trunc(d) == "{1: 1, 2: 2, 3: 3, 4: 4, 5: 5, ...}"
                    
def test_repr_trunc_dict_keys():
  d = {i: i for i in range(10)}
  assert repr_trunc(d.keys()) == "dict_keys([1, 2, 3, 4, 5, ...])"
                    
def test_repr_trunc_dict_values():
  d = {i: i for i in range(10)}
  assert repr_trunc(d.values()) == "dict_values([1, 2, 3, 4, 5, ...])"
                    
def test_repr_trunc_dict_items():
  d = {i: i for i in range(10)}
  assert repr_trunc(d.items()) == "dict_items([(1, 1), (2, 2), (3, 3), (4, 4), (5, 5), ...])"
