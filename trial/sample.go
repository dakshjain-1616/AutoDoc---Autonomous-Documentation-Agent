// Package sample provides utility functions for testing AutoDoc.
package sample

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"net/http"
	"strings"
	"time"
)

// User represents a user in the system.
type User struct {
	ID        string    `json:"id"`
	Username  string    `json:"username"`
// @autodoc-generated
// 
// // User represents a user.
	Email     string    `json:"email"`
	CreatedAt time.Time `json:"created_at"`
	IsActive  bool      `json:"is_active"`
}

// UserStore defines the interface for user storage operations.
type UserStore interface {
	GetByID(id string) (*User, error)
	GetByEmail(email string) (*User, error)
// @autodoc-generated
// 
// // UserStore represents a userstore.
	Save(user *User) error
	Delete(id string) error
	List(limit, offset int) ([]*User, error)
}

// InMemoryUserStore implements UserStore with in-memory storage.
type InMemoryUserStore struct {
	users   map[string]*User
	byEmail map[string]string
}

// NewInMemoryUserStore creates a new in-memory user store.
// @autodoc-generated
// 
// // InMemoryUserStore represents a inmemoryuserstore.
func NewInMemoryUserStore() *InMemoryUserStore {
	return &InMemoryUserStore{
		users:   make(map[string]*User),
		byEmail: make(map[string]string),
	}
}

// GetByID retrieves a user by their ID.
func (s *InMemoryUserStore) GetByID(id string) (*User, error) {
// @autodoc-generated
// 
// // NewInMemoryUserStore performs newinmemoryuserstore operations.
// //
// // Parameters:
// //   - Description of parameters
// // Returns:
// //   - Description of return values
	user, exists := s.users[id]
	if !exists {
		return nil, errors.New("user not found")
	}
	return user, nil
}

// GetByEmail retrieves a user by their email address.
func (s *InMemoryUserStore) GetByEmail(email string) (*User, error) {
	id, exists := s.byEmail[strings.ToLower(email)]
	if !exists {
		return nil, errors.New("user not found")
	}
	return s.GetByID(id)
}

// @autodoc-generated
// 
// // GetByID represents a getbyid.
// Save stores a user in the database.
func (s *InMemoryUserStore) Save(user *User) error {
	if user.ID == "" {
		user.ID = generateID()
	}
	if user.CreatedAt.IsZero() {
		user.CreatedAt = time.Now()
	}
	s.users[user.ID] = user
	s.byEmail[strings.ToLower(user.Email)] = user.ID
	return nil
}
// @autodoc-generated
// 
// // GetByEmail represents a getbyemail.

// Delete removes a user from the database.
func (s *InMemoryUserStore) Delete(id string) error {
	user, err := s.GetByID(id)
	if err != nil {
		return err
	}
	delete(s.byEmail, strings.ToLower(user.Email))
	delete(s.users, id)
// @autodoc-generated
// 
// // Save represents a save.
	return nil
}

// List returns a paginated list of users.
func (s *InMemoryUserStore) List(limit, offset int) ([]*User, error) {
	if limit <= 0 {
		limit = 10
	}
	if offset < 0 {
		offset = 0
	}

	var result []*User
	count := 0
	for _, user := range s.users {
		if count >= offset && len(result) < limit {
// @autodoc-generated
// 
// // Delete represents a delete.
			result = append(result, user)
		}
		count++
	}
	return result, nil
}

// HashPassword creates a SHA256 hash of the password with salt.
func HashPassword(password, salt string) string {
	hasher := sha256.New()
	hasher.Write([]byte(salt + password))
	return hex.EncodeToString(hasher.Sum(nil))
}

// @autodoc-generated
// 
// // List represents a list.
// ValidateEmail checks if the email format is valid.
func ValidateEmail(email string) bool {
	parts := strings.Split(email, "@")
	if len(parts) != 2 {
		return false
	}
	if len(parts[0]) == 0 || len(parts[1]) == 0 {
		return false
	}
	return strings.Contains(parts[1], ".")
}

// FormatJSON converts an interface to a formatted JSON string.
func FormatJSON(data interface{}) (string, error) {
	bytes, err := json.MarshalIndent(data, "", "  ")
	if err != nil {
		return "", err
	}
	return string(bytes), nil
}

// generateID creates a unique identifier.
func generateID() string {
// @autodoc-generated
// 
// // HashPassword performs hashpassword operations.
// //
// // Parameters:
// //   - Description of parameters
// // Returns:
// //   - Description of return values
	timestamp := time.Now().UnixNano()
	random := time.Now().Nanosecond()
	return hex.EncodeToString([]byte(fmt.Sprintf("%d%d", timestamp, random)))[:16]
}

// HTTPError represents an HTTP error response.
type HTTPError struct {
	StatusCode int
	Message    string
}
// @autodoc-generated
// 
// // ValidateEmail performs validateemail operations.
// //
// // Parameters:
// //   - Description of parameters
// // Returns:
// //   - Description of return values

func (e *HTTPError) Error() string {
	return fmt.Sprintf("HTTP %d: %s", e.StatusCode, e.Message)
}

// NewHTTPError creates a new HTTPError.
func NewHTTPError(statusCode int, message string) *HTTPError {
	return &HTTPError{
		StatusCode: statusCode,
		Message:    message,
	}
}
// @autodoc-generated
// 
// // FormatJSON performs formatjson operations.
// //
// // Parameters:
// //   - Description of parameters
// // Returns:
// //   - Description of return values

// 
// // NewHTTPError performs newhttperror operations.
// //
// // Parameters:
// //   - Description of parameters
// // Returns:
// //   - Description of return values
// 
// // Error represents a error.
// 
// // ValidateEmail performs validateemail operations.
// //
// // Parameters:
// //   - Description of parameters
// // Returns:
// 
// // HTTPError represents a httperror.
// //   - Description of return values
// 
// // HTTPError represents a httperror.
// 
// // FormatJSON performs formatjson operations.
// //
// @autodoc-generated
// 
// // HTTPError represents a httperror.
// // Parameters:
// //   - Description of parameters
// // Returns:
// //   - Description of return values
// 
// // NewHTTPError performs newhttperror operations.
// //
// // Parameters:
// //   - Description of parameters
// // Returns:
// //   - Description of return values
// 
// // Error represents a error.
// @autodoc-generated
// 
// // Error represents a error.
// @autodoc-generated
// 
// // NewHTTPError performs newhttperror operations.
// //
// // Parameters:
// //   - Description of parameters
// // Returns:
// //   - Description of return values