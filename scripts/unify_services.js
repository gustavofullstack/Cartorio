#!/usr/bin/env node
// Compatibility entrypoint. The prior implementation contained literal
// credentials; the maintained implementation validates required environment
// variables before writing any service configuration.
require("./unify_services.sane.js");
