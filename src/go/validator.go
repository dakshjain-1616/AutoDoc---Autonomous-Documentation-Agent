package validator

import (
	"errors"
	"fmt"
	"regexp"
	"strings"
)

// @autodoc-generated
// ValidationRule represents a validationrule.
//
// This type provides functionality for working with validationrule data.
type ValidationRule struct {
	Field   string
	Check   func(interface{}) error
	Message string
}

// @autodoc-generated
// Validator represents a validator.
//
// This type provides functionality for working with validator data.
type Validator struct {
	rules  []ValidationRule
	errors map[string][]string
}

// @autodoc-generated
// New performs new operations.
//
// Parameters:
//   - Description of parameters and their types
//
// Returns:
//   - Description of return values and their meaning
//
// Example:
//   result := New()
//   fmt.Println(result)
func New() *Validator {
	return &Validator{
		rules:  make([]ValidationRule, 0),
		errors: make(map[string][]string),
	}
}

// @autodoc-generated
// AddRule represents a addrule.
//
// This type provides functionality for working with addrule data.
func (v *Validator) AddRule(field string, check func(interface{}) error, message string) {
	v.rules = append(v.rules, ValidationRule{
		Field:   field,
		Check:   check,
		Message: message,
	})
}

// @autodoc-generated
// Validate represents a validate.
//
// This type provides functionality for working with validate data.
func (v *Validator) Validate(data map[string]interface{}) bool {
	v.errors = make(map[string][]string)
	isValid := true

	for _, rule := range v.rules {
		value, exists := data[rule.Field]
		if !exists {
			v.errors[rule.Field] = append(v.errors[rule.Field], "Field is required")
			isValid = false
			continue
		}

		if err := rule.Check(value); err != nil {
			v.errors[rule.Field] = append(v.errors[rule.Field], rule.Message)
			isValid = false
		}
	}

	return isValid
}

// @autodoc-generated
// GetErrors represents a geterrors.
//
// This type provides functionality for working with geterrors data.
func (v *Validator) GetErrors() map[string][]string {
	return v.errors
}

// @autodoc-generated
// Required performs required operations.
//
// Parameters:
//   - Description of parameters and their types
//
// Returns:
//   - Description of return values and their meaning
//
// Example:
//   result := Required()
//   fmt.Println(result)
func Required() func(interface{}) error {
	return func(value interface{}) error {
		if value == nil || value == "" {
			return errors.New("value is required")
		}
		return nil
	}
}

// @autodoc-generated
// MinLength performs minlength operations.
//
// Parameters:
//   - Description of parameters and their types
//
// Returns:
//   - Description of return values and their meaning
//
// Example:
//   result := MinLength()
//   fmt.Println(result)
func MinLength(min int) func(interface{}) error {
	return func(value interface{}) error {
		str, ok := value.(string)
		if !ok {
			return errors.New("value must be a string")
		}
		if len(str) < min {
			return fmt.Errorf("value must be at least %d characters", min)
		}
		return nil
	}
}

// @autodoc-generated
// Email performs email operations.
//
// Parameters:
//   - Description of parameters and their types
//
// Returns:
//   - Description of return values and their meaning
//
// Example:
//   result := Email()
//   fmt.Println(result)
func Email() func(interface{}) error {
	emailRegex := regexp.MustCompile(`^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$`)
	return func(value interface{}) error {
		str, ok := value.(string)
		if !ok {
			return errors.New("value must be a string")
		}
		if !emailRegex.MatchString(str) {
			return errors.New("invalid email format")
		}
		return nil
	}
}

// @autodoc-generated
// Matches performs matches operations.
//
// Parameters:
//   - Description of parameters and their types
//
// Returns:
//   - Description of return values and their meaning
//
// Example:
//   result := Matches()
//   fmt.Println(result)
func Matches(pattern string) func(interface{}) error {
	re := regexp.MustCompile(pattern)
	return func(value interface{}) error {
		str, ok := value.(string)
		if !ok {
			return errors.New("value must be a string")
		}
		if !re.MatchString(str) {
			return fmt.Errorf("value does not match pattern: %s", pattern)
		}
		return nil
	}
}

// keep strings import used
var _ = strings.TrimSpace
