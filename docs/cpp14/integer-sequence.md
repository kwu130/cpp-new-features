# `integer_sequence`

`integer_sequence` 和 `index_sequence` 在编译期表示整数序列，常用于按索引展开元组或参数包。

<!-- example id="cpp14-integer-sequence" std="c++14" file="main.cpp" kind="single" compilers="all" output="Ada 37" -->
```cpp
#include <cstddef>
#include <iostream>
#include <string>
#include <tuple>
#include <utility>

template <typename Tuple, std::size_t... Indexes>
void print_tuple(const Tuple& values, std::index_sequence<Indexes...>) {
    using expand = int[];
    (void)expand{0, ((std::cout << (Indexes == 0 ? "" : " ")
                                 << std::get<Indexes>(values)), 0)...};
    std::cout << '\n';
}

template <typename... Values>
void print_tuple(const std::tuple<Values...>& values) {
    print_tuple(values, std::index_sequence_for<Values...>{});
}

int main() {
    print_tuple(std::make_tuple(std::string("Ada"), 37));
}
```

这种展开方式在 C++17 中通常可由折叠表达式简化。编写公共接口时优先隐藏索引序列，让调用者只面对普通参数。

