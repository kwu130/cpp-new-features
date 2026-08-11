# 保证的复制消除

C++17 在若干纯右值初始化场景中保证对象直接构造到最终存储位置，即使类型不能复制也不能移动，代码仍然合法。

<!-- example id="cpp17-copy-elision" std="c++17" file="main.cpp" kind="single" compilers="all" output="token=42" -->
```cpp
#include <iostream>

class Token {
public:
    explicit Token(int value) : value_(value) {}
    Token(const Token&) = delete;
    Token(Token&&) = delete;
    int value() const { return value_; }

private:
    int value_;
};

Token make_token() {
    return Token(42);
}

int main() {
    Token token = make_token();
    std::cout << "token=" << token.value() << '\n';
}
```

保证适用于直接返回同类型纯右值等规定场景；返回具名局部变量依赖 NRVO，仍不是语言强制保证。析构函数在相关上下文中仍必须可访问。

